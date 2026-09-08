import 'dart:async';
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

  DocumentStabilityDetector({
    required this.controller,
    required this.onStable,
    this.onProgress,
    this.stabilityThreshold = 4.5,
    this.requiredStableFrames = 28,
    this.initialSettlingFrames = 24,
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

    if (mad < stabilityThreshold) {
      _stableStreak++;
    } else {
      // If motion detected, quickly decay rather than instant zero to avoid jitter
      _stableStreak = (_stableStreak > 3) ? _stableStreak - 3 : 0;
    }

    final progress = (_stableStreak / requiredStableFrames).clamp(0.0, 1.0);
    onProgress?.call(progress);

    if (_stableStreak >= requiredStableFrames) {
      _hasFired = true;
      onStable();
    }
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
