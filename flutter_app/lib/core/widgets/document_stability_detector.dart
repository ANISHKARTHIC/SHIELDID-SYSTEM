import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';
import 'package:camera/camera.dart';

/// Lightweight on-device "hold it steady" auto-capture trigger for the
/// document scan screen.
///
/// Unlike naive whole-frame average brightness (which doesn't detect
/// camera panning or translation across a table), this samples a coarse grid
/// of luminance values and calculates the Mean Absolute Difference (MAD)
/// across corresponding pixels between consecutive frames:
///   MAD = sum(|I_t(x,y) - I_{t-1}(x,y)|) / N
/// Panning or moving the phone results in high MAD (> 12-40), while holding
/// the phone still over the document drops MAD below [stabilityThreshold] (< 4.5).
///
/// Includes an initial settling delay so opening the camera never snaps
/// prematurely, and reports [onProgress] (0.0 -> 1.0) so the UI can show
/// the user visual locking progress.
class DocumentStabilityDetector {
  final CameraController controller;
  final void Function() onStable;
  final void Function(double progress)? onProgress;

  /// Mean Absolute Difference threshold (0-255 scale) below which two
  /// consecutive sampled frames are treated as stationary.
  final double stabilityThreshold;

  /// How many consecutive stable frames are required before firing (~1s at 30fps).
  final int requiredStableFrames;

  /// Grace period in frames before stability counting begins (~1.0s at 30fps)
  /// so opening the camera gives the user time to position the document.
  final int initialSettlingFrames;

  bool _isStreaming = false;
  bool _hasFired = false;
  Uint8List? _lastSampledGrid;
  int _stableStreak = 0;
  int _totalFramesSeen = 0;

  /// Sharpness (mean absolute horizontal gradient) of the most recently sampled frame.
  double? get lastSharpness => _lastSharpness;
  double? _lastSharpness;

  /// Minimum luminance standard deviation (0-255 scale) within the central
  /// guide region for a frame to be considered "has document-like content."
  /// A blank wall, table, or out-of-focus void produces a low value here;
  /// a card with text/photo/borders produces a much higher one. Without
  /// this, stillness alone (e.g. pointing at a blank surface) satisfies
  /// the MAD stability check and fires a capture with no document in frame.
  final double minContentVariance;

  DocumentStabilityDetector({
    required this.controller,
    required this.onStable,
    this.onProgress,
    this.stabilityThreshold = 4.5,
    this.requiredStableFrames = 28,
    this.initialSettlingFrames = 24,
    this.minContentVariance = 18.0,
  });

  void start() {
    if (_isStreaming || !controller.value.isInitialized) return;
    _isStreaming = true;
    _hasFired = false;
    _lastSampledGrid = null;
    _lastSharpness = null;
    _stableStreak = 0;
    _totalFramesSeen = 0;
    onProgress?.call(0.0);
    controller.startImageStream(_onFrame);
  }

  Future<void> stop() async {
    if (!_isStreaming) return;
    _isStreaming = false;
    try {
      await controller.stopImageStream();
    } catch (_) {}
    onProgress?.call(0.0);
  }

  /// Re-arms detection for another capture without restarting the stream.
  void reset() {
    _hasFired = false;
    _lastSampledGrid = null;
    _stableStreak = 0;
    _totalFramesSeen = 0;
    onProgress?.call(0.0);
  }

  void _onFrame(CameraImage image) {
    if (_hasFired || image.planes.isEmpty) return;

    final yPlane = image.planes.first;
    final currentGrid = _sampleGrid(
      yPlane.bytes,
      image.width,
      image.height,
      yPlane.bytesPerRow,
    );
    _lastSharpness = _sampledSharpness(
      yPlane.bytes,
      image.width,
      image.height,
      yPlane.bytesPerRow,
    );

    _totalFramesSeen++;
    final prevGrid = _lastSampledGrid;
    _lastSampledGrid = currentGrid;

    if (prevGrid == null || _totalFramesSeen < initialSettlingFrames) {
      onProgress?.call(0.0);
      return;
    }

    final mad = _computeMAD(currentGrid, prevGrid);
    final hasContent = _centralRegionVariance(
          yPlane.bytes,
          image.width,
          image.height,
          yPlane.bytesPerRow,
        ) >=
        minContentVariance;

    if (mad < stabilityThreshold && hasContent) {
      _stableStreak++;
    } else {
      // If motion detected, or the guide area is just blank wall/table
      // with nothing document-like in it, quickly decay rather than
      // instant zero to avoid jitter.
      _stableStreak = (_stableStreak > 3) ? _stableStreak - 3 : 0;
    }

    final progress = (_stableStreak / requiredStableFrames).clamp(0.0, 1.0);
    onProgress?.call(progress);

    if (_stableStreak >= requiredStableFrames) {
      _hasFired = true;
      onStable();
    }
  }

  /// Standard deviation of luma within the central ~55% x ~55% of the
  /// frame — a coarse proxy for "does the guide-box area contain a
  /// document" (text/photo/border edges) vs. a blank wall or tabletop
  /// (near-uniform luma, low variance).
  double _centralRegionVariance(
    Uint8List yPlane,
    int width,
    int height,
    int bytesPerRow,
  ) {
    const stride = 8;
    final left = (width * 0.225).round();
    final right = (width * 0.775).round();
    final top = (height * 0.225).round();
    final bottom = (height * 0.775).round();

    double sum = 0;
    double sumSq = 0;
    int count = 0;
    for (int y = top; y < bottom; y += stride) {
      final rowStart = y * bytesPerRow;
      if (rowStart >= yPlane.length) break;
      for (int x = left; x < right; x += stride) {
        final pos = rowStart + x;
        if (pos >= yPlane.length) break;
        final v = yPlane[pos].toDouble();
        sum += v;
        sumSq += v * v;
        count++;
      }
    }
    if (count == 0) return 0;
    final mean = sum / count;
    final variance = (sumSq / count) - (mean * mean);
    return variance <= 0 ? 0 : math.sqrt(variance);
  }

  /// Samples a downsampled 1D array of luma points (stride = 16)
  /// For 1280x720, this creates ~3,600 bytes, which is extremely lightweight.
  Uint8List _sampleGrid(Uint8List yPlane, int width, int height, int bytesPerRow) {
    const stride = 16;
    final gridWidth = (width + stride - 1) ~/ stride;
    final gridHeight = (height + stride - 1) ~/ stride;
    final buffer = Uint8List(gridWidth * gridHeight);

    int idx = 0;
    for (int y = 0; y < height; y += stride) {
      final rowStart = y * bytesPerRow;
      if (rowStart >= yPlane.length) break;
      for (int x = 0; x < width; x += stride) {
        final pos = rowStart + x;
        if (pos < yPlane.length && idx < buffer.length) {
          buffer[idx++] = yPlane[pos];
        }
      }
    }
    return buffer;
  }

  /// Computes Mean Absolute Difference between two sampled grids of identical length.
  double _computeMAD(Uint8List a, Uint8List b) {
    final len = a.length < b.length ? a.length : b.length;
    if (len == 0) return 999.0;

    int diffSum = 0;
    for (int i = 0; i < len; i++) {
      diffSum += (a[i] - b[i]).abs();
    }
    return diffSum / len;
  }

  /// Mean absolute horizontal gradient over a coarse grid as a focus proxy.
  double _sampledSharpness(Uint8List yPlane, int width, int height, int bytesPerRow) {
    const stride = 8;
    int sum = 0;
    int count = 0;
    for (int y = 0; y < height; y += stride) {
      final rowStart = y * bytesPerRow;
      if (rowStart >= yPlane.length) break;
      int? prev;
      for (int x = 0; x < width; x += stride) {
        final index = rowStart + x;
        if (index >= yPlane.length) break;
        final val = yPlane[index];
        if (prev != null) {
          sum += (val - prev).abs();
          count++;
        }
        prev = val;
      }
    }
    return count == 0 ? 0 : sum / count;
  }
}
