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
    _takePicture();
  }

  Future<void> _takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    if (_isCapturing) return;
    _isCapturing = true;

    try {
      // takePicture() can't run while the image stream (used for
      // auto-capture stability detection) is active on most platforms —
      // stop it first, whether this capture was triggered by the
      // detector itself or a manual shutter tap.
      await _stabilityDetector?.stop();
      final image = await _controller!.takePicture();
      _navigateToReview(image.path);
    } catch (e) {
      _isCapturing = false;
      _stabilityDetector?.reset();
      _stabilityDetector?.start();
      if (mounted) {
        setState(() => _error = 'Could not capture photo. Please try again.');
      }
    }
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);

    if (image != null) {
      _navigateToReview(image.path);
    }
  }

  void _navigateToReview(String path) {
    if (mounted) {
      Navigator.of(context).push(
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
