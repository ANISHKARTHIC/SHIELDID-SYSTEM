import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import 'ocr_review_view.dart';
import '../../../../core/widgets/camera_scaffold.dart';
import '../../../../core/widgets/document_stability_detector.dart';
import '../../../../core/navigation/app_page_route.dart';
import '../../../../core/security/camera_permission_service.dart';

class CameraView extends StatefulWidget {
  final String sessionId;
  const CameraView({super.key, required this.sessionId});

  @override
  State<CameraView> createState() => _CameraViewState();
}

class _CameraViewState extends State<CameraView> {
  CameraController? _controller;
  DocumentStabilityDetector? _stabilityDetector;
  bool _isCameraInitialized = false;
  bool _isCapturing = false;
  String? _error;
  final _scaffoldKey = GlobalKey<CameraCaptureScaffoldState>();

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final permission = await CameraPermissionService.ensureGranted();
    if (!permission.granted) {
      if (mounted) {
        setState(() {
          _error = permission.permanentlyDenied
              ? 'Camera access is disabled for VenuePass. Open Settings to enable it, or use Upload instead.'
              : 'Camera access is required to scan an ID. Please allow it, or use Upload instead.';
        });
      }
      return;
    }

    final cameras = await availableCameras();
    if (cameras.isEmpty) {
      if (mounted) {
        setState(() => _error = 'No camera is available on this device.');
      }
      return;
    }

    // Document scanning always needs the back camera — `cameras.first`
    // isn't guaranteed to be the back lens on every device/plugin build,
    // so select it explicitly instead of relying on list ordering.
    final backCamera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );

    _controller = CameraController(
      backCamera,
      ResolutionPreset.high,
      enableAudio: false,
    );

    try {
      await _controller!.initialize();
      try {
        await _controller!.setFocusMode(FocusMode.auto);
      } catch (_) {}
      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
        });
        // Auto-capture: fires once the framed scene holds steady for
        // ~0.8s, which reads as "document is in frame and the phone has
        // stopped moving" without needing real document/edge detection.
        // Manual shutter tap still works at any time — whichever fires
        // first wins, guarded by _isCapturing below.
        _stabilityDetector = DocumentStabilityDetector(
          controller: _controller!,
          onStable: _onDocumentStable,
        )..start();
      }
    } catch (e) {
      if (mounted) {
        setState(
          () => _error = 'Could not start the camera. Please try again.',
        );
      }
    }
  }

  @override
  void dispose() {
    _stabilityDetector?.stop();
    _controller?.dispose();
    super.dispose();
  }

  void _onDocumentStable() {
    if (_isCapturing || !mounted) return;
    // Auto-capture has no tap to hang the usual haptic+flash feedback
    // off of — trigger it explicitly so it's just as visible/felt as a
    // manual shutter press, instead of silently jumping to the review
    // screen with no confirmation a photo was taken at all.
    _scaffoldKey.currentState?.triggerCaptureFeedback();
    _takePicture(checkSharpness: true);
  }

  /// Below this mean-gradient score the frame is treated as too blurry to
  /// send straight to OCR — tuned against real captures: a sharp,
  /// in-focus document scan reads comfortably above 10 on this scale,
  /// while a blurry/motion-smeared one reads under 4-5. Only gates the
  /// auto-capture path (see [_takePicture]'s `checkSharpness` param) since
  /// the stability detector's image stream — the only source for this
  /// score — isn't running for a manual shutter tap that fires before
  /// stability was reached.
  static const _minAcceptableSharpness = 6.0;

  Future<void> _takePicture({bool checkSharpness = false}) async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    if (_isCapturing) return;
    setState(() => _isCapturing = true);

    final sharpness = _stabilityDetector?.lastSharpness;

    try {
      // takePicture() can't run while the image stream (used for
      // auto-capture stability detection) is active on most platforms —
      // stop it first, whether this capture was triggered by the
      // detector itself or a manual shutter tap.
      await _stabilityDetector?.stop();

      if (checkSharpness &&
          sharpness != null &&
          sharpness < _minAcceptableSharpness) {
        // Stable (motion-wise) but still out of focus — e.g. auto-focus
        // still hunting, or held too close. Skip the capture entirely and
        // let the detector keep watching rather than snapping a photo
        // that's just going to fail OCR downstream.
        if (mounted) {
          setState(() => _isCapturing = false);
          _stabilityDetector?.reset();
          _stabilityDetector?.start();
        }
        return;
      }

      final image = await _controller!.takePicture();

      if (checkSharpness &&
          sharpness != null &&
          sharpness < _minAcceptableSharpness * 1.5 &&
          mounted) {
        final shouldRetake = await _confirmBlurryCapture();
        if (shouldRetake == true) {
          if (mounted) {
            setState(() => _isCapturing = false);
            _stabilityDetector?.reset();
            _stabilityDetector?.start();
          }
          return;
        }
      }

      await _navigateToReview(image.path);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Could not capture photo. Please try again.');
      }
    } finally {
      if (mounted) {
        setState(() => _isCapturing = false);
        _stabilityDetector?.reset();
        _stabilityDetector?.start();
      }
    }
  }

  /// Manual clarity gate for a borderline-sharp auto-capture: shows the
  /// captured photo and asks staff to confirm it's legible rather than
  /// silently sending a marginal photo straight to OCR (which is where a
  /// soft-focus capture actually surfaces as a failed/garbled extraction
  /// several seconds later, far from the moment it could cheaply be
  /// retaken).
  Future<bool?> _confirmBlurryCapture() {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Photo may be blurry'),
        content: const Text(
          'This capture looks a little out of focus, which can cause '
          'incorrect data extraction. Use it anyway, or retake?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Retake'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Use Photo'),
          ),
        ],
      ),
    );
  }

  Future<void> _pickImage() async {
    if (_isCapturing) return;
    final picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);

    if (image != null) {
      setState(() => _isCapturing = true);
      try {
        await _stabilityDetector?.stop();
        await _navigateToReview(image.path);
      } catch (e) {
        if (mounted) {
          setState(() => _error = 'Could not load selected photo.');
        }
      } finally {
        if (mounted) {
          setState(() => _isCapturing = false);
          _stabilityDetector?.reset();
          _stabilityDetector?.start();
        }
      }
    }
  }

  Future<void> _navigateToReview(String path) async {
    if (mounted) {
      await Navigator.of(context).push(
        AppPageRoute.push(
          OCRReviewView(imagePath: path, sessionId: widget.sessionId),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return CameraCaptureScaffold(
      key: _scaffoldKey,
      controller: _controller,
      isInitializing: !_isCameraInitialized,
      instructionText: 'Hold steady — captures automatically when aligned',
      errorText: _error,
      currentStep: 1,
      totalSteps: 3,
      stepLabel: 'Scan Document',
      onCapture: _takePicture,
      onPickFromGallery: _pickImage,
      onClose: () => Navigator.pop(context),
    );
  }
}
