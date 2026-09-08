import 'dart:io';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

/// Crops a just-captured photo down to the on-screen guide rectangle shown
/// in [CameraCaptureScaffold], so the server (and OCR) only ever sees what
/// the user actually framed instead of the whole scene — desk, hands,
/// laptop, wall, etc.
///
/// [CameraPreview] renders the live feed inside an `AspectRatio` box sized
/// to the camera's native aspect ratio, letterboxed/pillarboxed to fit the
/// screen (see the `camera` package's `CameraPreview.build`). The guide
/// rectangle drawn in `CameraCaptureScaffold` is positioned relative to the
/// full screen, centered, sized `screenWidth * widthFactor` x
/// `screenWidth * heightFactor`. To crop the captured file correctly we:
///
/// 1. Reconstruct the same letterboxed preview rect from screen size +
///    camera aspect ratio (matching `AspectRatio`'s fit-within behavior).
/// 2. Intersect the guide rectangle with that preview rect (guide can
///    slightly overhang letterbox bars on extreme aspect mismatches).
/// 3. Map the intersected rect from preview-space to captured-image-pixel
///    space (accounting for `image`'s EXIF-aware decode, and for the
///    portrait vs. landscape sensor/screen orientation swap).
class GuideFrameCropper {
  /// Crops [imagePath] to the guide rectangle and overwrites the file in
  /// place. Returns the (possibly unchanged) path. Never throws — if
  /// anything about the geometry looks wrong, it leaves the original photo
  /// intact rather than risk cropping out the actual document.
  static Future<String> cropToGuide({
    required String imagePath,
    required CameraController controller,
    required double screenWidth,
    required double screenHeight,
    required double guideWidthFactor,
    required double guideHeightFactor,
    required bool isOvalGuide,
  }) async {
    try {
      final bytes = await File(imagePath).readAsBytes();
      final decoded = img.decodeImage(bytes);
      if (decoded == null) return imagePath;

      // Normalize EXIF rotation so pixel coordinates below match what a
      // viewer actually sees (and what the guide rect was drawn against).
      final oriented = img.bakeOrientation(decoded);
      final imgW = oriented.width.toDouble();
      final imgH = oriented.height.toDouble();

      // The sensor is naturally landscape; `CameraPreview` swaps the
      // aspect ratio for portrait display. Mirror that here so our
      // reconstructed preview box matches what was on screen.
      final sensorAspect = controller.value.aspectRatio;
      final isPortraitDevice = screenHeight >= screenWidth;
      final previewAspect = isPortraitDevice ? (1 / sensorAspect) : sensorAspect;

      // `AspectRatio` fits the largest box of `previewAspect` inside the
      // screen bounds (BoxFit.contain semantics), centered.
      double previewW = screenWidth;
      double previewH = screenWidth / previewAspect;
      if (previewH > screenHeight) {
        previewH = screenHeight;
        previewW = screenHeight * previewAspect;
      }
      final previewLeft = (screenWidth - previewW) / 2;
      final previewTop = (screenHeight - previewH) / 2;

      // Guide rect, centered on screen (matches camera_scaffold.dart).
      final guideW = screenWidth * guideWidthFactor;
      final guideH = screenWidth * guideHeightFactor;
      final guideLeft = (screenWidth - guideW) / 2;
      final guideTop = (screenHeight - guideH) / 2;

      // Intersect guide with the visible preview area (drop any part that
      // falls on a letterbox bar — there's no image data there).
      final left = guideLeft.clamp(previewLeft, previewLeft + previewW);
      final top = guideTop.clamp(previewTop, previewTop + previewH);
      final right = (guideLeft + guideW).clamp(previewLeft, previewLeft + previewW);
      final bottom = (guideTop + guideH).clamp(previewTop, previewTop + previewH);
      if (right <= left || bottom <= top) return imagePath;

      // Map from preview-space (0..previewW/H) to image-pixel-space.
      final scaleX = imgW / previewW;
      final scaleY = imgH / previewH;

      var cropX = ((left - previewLeft) * scaleX).round();
      var cropY = ((top - previewTop) * scaleY).round();
      var cropW = ((right - left) * scaleX).round();
      var cropH = ((bottom - top) * scaleY).round();

      // A little safety margin so a slightly-misjudged edge doesn't slice
      // into the document itself.
      const marginFactor = 0.04;
      final marginX = (cropW * marginFactor).round();
      final marginY = (cropH * marginFactor).round();
      cropX = (cropX - marginX).clamp(0, imgW.toInt());
      cropY = (cropY - marginY).clamp(0, imgH.toInt());
      cropW = (cropW + marginX * 2).clamp(1, imgW.toInt() - cropX);
      cropH = (cropH + marginY * 2).clamp(1, imgH.toInt() - cropY);

      if (cropW < 20 || cropH < 20) return imagePath;

      final cropped = img.copyCrop(
        oriented,
        x: cropX,
        y: cropY,
        width: cropW,
        height: cropH,
      );

      final Uint8List encoded = Uint8List.fromList(img.encodeJpg(cropped, quality: 92));
      await File(imagePath).writeAsBytes(encoded, flush: true);
      return imagePath;
    } catch (_) {
      // Never block capture on a cropping failure — fall back to the
      // full, uncropped photo rather than losing the capture entirely.
      return imagePath;
    }
  }
}
