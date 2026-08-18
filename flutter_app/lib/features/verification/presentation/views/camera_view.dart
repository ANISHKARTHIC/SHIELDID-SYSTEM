import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import 'ocr_review_view.dart';
import '../../../../core/widgets/camera_scaffold.dart';
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
  bool _isCameraInitialized = false;
  String? _error;

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
      if (mounted) setState(() => _error = 'No camera is available on this device.');
      return;
    }

    _controller = CameraController(
      cameras.first,
      ResolutionPreset.high,
      enableAudio: false,
    );

    try {
      await _controller!.initialize();
      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not start the camera. Please try again.');
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    try {
      final image = await _controller!.takePicture();
      _navigateToReview(image.path);
    } catch (e) {
      if (mounted) setState(() => _error = 'Could not capture photo. Please try again.');
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
      controller: _controller,
      isInitializing: !_isCameraInitialized,
      instructionText: 'Align identity document inside the frame',
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
