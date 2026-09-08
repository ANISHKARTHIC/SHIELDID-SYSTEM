import 'dart:async';
import 'dart:typed_data';
import 'package:camera/camera.dart';

/// Lightweight on-device "hold it steady" auto-capture trigger for the
/// document scan screen — not real document/rectangle detection (that
/// needs real CV inference and a much heavier plugin/model), but a cheap
/// stability heuristic that approximates "a document is framed and the
/// camera has stopped moving," which is what actually matters for a
/// clean capture. Costs one downsampled luma-plane diff per frame, no
/// image decode/allocation beyond that — safe to run continuously on a
/// mid-range Android device.
///
/// How it works: samples the Y (luminance) plane of each YUV420 camera
/// frame at a coarse stride (every 8th pixel — plenty to detect motion,
/// far cheaper than a full-resolution diff), compares mean luma against
/// the previous sampled frame, and treats the frame as "stable" when the
/// change is below [stabilityThreshold]. Once [requiredStableFrames]
/// consecutive frames are stable, [onStable] fires exactly once (call
/// [reset] to re-arm after handling it, e.g. after a capture completes or
/// the guide frame is left).
class DocumentStabilityDetector {
  final CameraController controller;
  final void Function() onStable;

  /// Mean-luma delta (0-255 scale) below which two consecutive frames
  /// count as "the same" — tuned loose enough to tolerate sensor noise on
  /// a static scene but tight enough to reject a hand still moving the
  /// phone into position.
  final double stabilityThreshold;

  /// How many consecutive stable frames are required before firing —
  /// at the camera's frame rate this is roughly requiredStableFrames/30s,
  /// e.g. 24 frames ≈ 0.8s of hold-still.
  final int requiredStableFrames;

  bool _isStreaming = false;
  bool _hasFired = false;
  double? _lastMeanLuma;
  int _stableStreak = 0;

  /// Sharpness (mean absolute horizontal gradient over the same coarse
  /// luma grid used for stability) of the most recently sampled frame —
  /// a stationary phone can still be out of focus (auto-focus still
  /// hunting, macro distance too close), so "stable" alone doesn't mean
  /// "sharp." Read by the caller at the moment [onStable] fires to decide
  /// whether to accept the capture or prompt a retake.
  double? get lastSharpness => _lastSharpness;
  double? _lastSharpness;

  DocumentStabilityDetector({
    required this.controller,
    required this.onStable,
    this.stabilityThreshold = 2.5,
    this.requiredStableFrames = 24,
  });

  void start() {
    if (_isStreaming || !controller.value.isInitialized) return;
    _isStreaming = true;
    _hasFired = false;
    _lastMeanLuma = null;
    _lastSharpness = null;
    _stableStreak = 0;
    controller.startImageStream(_onFrame);
  }

  Future<void> stop() async {
    if (!_isStreaming) return;
    _isStreaming = false;
    try {
      await controller.stopImageStream();
    } catch (_) {
      // Controller may already be mid-dispose (e.g. screen popped while a
      // frame callback was in flight) — nothing to clean up in that case.
    }
  }

  /// Re-arms detection for another capture without restarting the stream
  /// (e.g. after the user retakes, or after this fired once).
  void reset() {
    _hasFired = false;
    _lastMeanLuma = null;
    _stableStreak = 0;
  }

  void _onFrame(CameraImage image) {
    if (_hasFired || image.planes.isEmpty) return;

    final yPlane = image.planes.first;
    final meanLuma = _sampledMeanLuma(yPlane.bytes, image.width, image.height, yPlane.bytesPerRow);
    _lastSharpness = _sampledSharpness(yPlane.bytes, image.width, image.height, yPlane.bytesPerRow);

    final last = _lastMeanLuma;
    _lastMeanLuma = meanLuma;
    if (last == null) return;

    final delta = (meanLuma - last).abs();
    if (delta < stabilityThreshold) {
      _stableStreak++;
    } else {
      _stableStreak = 0;
    }

    if (_stableStreak >= requiredStableFrames) {
      _hasFired = true;
      onStable();
    }
  }

  /// Mean luma over a coarse grid (every 8th pixel in both dimensions) —
  /// O(width/8 * height/8) instead of a full-resolution pass, which is
  /// the difference between "runs fine on every frame" and "drops frames
  /// on a mid-range device."
  double _sampledMeanLuma(Uint8List yPlane, int width, int height, int bytesPerRow) {
    const stride = 8;
    int sum = 0;
    int count = 0;
    for (int y = 0; y < height; y += stride) {
      final rowStart = y * bytesPerRow;
      if (rowStart >= yPlane.length) break;
      for (int x = 0; x < width; x += stride) {
        final index = rowStart + x;
        if (index >= yPlane.length) break;
        sum += yPlane[index];
        count++;
      }
    }
    return count == 0 ? 0 : sum / count;
  }

  /// Cheap focus proxy: mean absolute luma difference between
  /// horizontally-adjacent sampled pixels over the same coarse grid used
  /// by [_sampledMeanLuma]. A sharp, in-focus image has strong local
  /// edges (high gradient); a blurry/out-of-focus one smears them out
  /// (low gradient) — this is a simplified single-axis stand-in for a
  /// full Laplacian-variance blur score, cheap enough to run on every
  /// streamed frame on a mid-range device.
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
