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
  bool _autoCaptureEnabled = false;
  double _stabilityProgress = 0.0;
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

    // Document scanning always needs the back camera
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

        _stabilityDetector = DocumentStabilityDetector(
          controller: _controller!,
          onStable: _onDocumentStable,
          onProgress: (progress) {
            if (mounted && _autoCaptureEnabled) {
              setState(() => _stabilityProgress = progress);
            }
          },
        );

        if (_autoCaptureEnabled) {
          _stabilityDetector?.start();
        }
      }
    } catch (e) {
      if (mounted) {
        setState(
          () => _error = 'Could not start the camera. Please try again.',
        );
      }
    }
  }

  void _toggleAutoCapture() {
    setState(() {
      _autoCaptureEnabled = !_autoCaptureEnabled;
      _stabilityProgress = 0.0;
    });
    if (_autoCaptureEnabled) {
      _stabilityDetector?.reset();
      _stabilityDetector?.start();
    } else {
      _stabilityDetector?.stop();
    }
  }

  @override
  void dispose() {
    _stabilityDetector?.stop();
    _controller?.dispose();
    super.dispose();
  }

  void _onDocumentStable() {
    if (_isCapturing || !_autoCaptureEnabled || !mounted) return;
    _scaffoldKey.currentState?.triggerCaptureFeedback();
    _takePicture(checkSharpness: true);
  }

  static const _minAcceptableSharpness = 5.5;

  Future<void> _takePicture({bool checkSharpness = false}) async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    if (_isCapturing) return;
    setState(() => _isCapturing = true);

    final sharpness = _stabilityDetector?.lastSharpness;

    try {
      await _stabilityDetector?.stop();

      // If auto-capture triggered on a blurry frame, quietly reset and wait
      // rather than showing an intrusive popup dialog.
      if (checkSharpness &&
          sharpness != null &&
          sharpness < _minAcceptableSharpness) {
        if (mounted) {
          setState(() {
            _isCapturing = false;
            _stabilityProgress = 0.0;
          });
          if (_autoCaptureEnabled) {
            _stabilityDetector?.reset();
            _stabilityDetector?.start();
          }
        }
        return;
      }

      final image = await _controller!.takePicture();
      await _navigateToReview(image.path);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Could not capture photo. Please try again.');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isCapturing = false;
          _stabilityProgress = 0.0;
        });
        if (_autoCaptureEnabled) {
          _stabilityDetector?.reset();
          _stabilityDetector?.start();
        }
      }
    }
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
          setState(() {
            _isCapturing = false;
            _stabilityProgress = 0.0;
          });
          if (_autoCaptureEnabled) {
            _stabilityDetector?.reset();
            _stabilityDetector?.start();
          }
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
      instructionText: _autoCaptureEnabled
          ? 'Hold steady — captures automatically when aligned'
          : 'Align ID in frame and tap shutter to capture',
      errorText: _error,
      currentStep: 1,
      totalSteps: 3,
      stepLabel: 'Scan Document',
      onCapture: _takePicture,
      onPickFromGallery: _pickImage,
      onClose: () => Navigator.pop(context),
      isAutoCaptureEnabled: _autoCaptureEnabled,
      onToggleAutoCapture: _toggleAutoCapture,
      stabilityProgress: _stabilityProgress,
    );
  }
}
