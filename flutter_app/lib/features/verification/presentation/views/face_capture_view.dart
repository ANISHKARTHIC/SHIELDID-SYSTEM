import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'decision_view.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/widgets/camera_scaffold.dart';
import '../../../../core/navigation/app_page_route.dart';
import '../../../../core/security/camera_permission_service.dart';

class FaceCaptureView extends StatefulWidget {
  final String sessionId;
  final Map<String, String> ocrData;

  const FaceCaptureView({
    super.key,
    required this.sessionId,
    required this.ocrData,
  });

  @override
  State<FaceCaptureView> createState() => _FaceCaptureViewState();
}

class _FaceCaptureViewState extends State<FaceCaptureView> {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  int _selectedCameraIndex = 0;
  bool _isCameraInitialized = false;
  bool _isSwitchingCamera = false;
  bool _isProcessing = false;
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
              : 'Camera access is required to verify your identity. Please allow it, or use Upload instead.';
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
    _cameras = cameras;

    // Default to the back camera: it captures a sharper, better-lit photo
    // than most phones' front/selfie camera, which improves face-match
    // accuracy. A switch button lets the user swap to the front camera
    // when they can't comfortably hold the phone facing away from them.
    int backIndex = cameras.indexWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
    );
    _selectedCameraIndex = backIndex >= 0 ? backIndex : 0;

    await _startCamera(_cameras[_selectedCameraIndex]);
  }

  Future<void> _startCamera(CameraDescription description) async {
    // The old controller's native camera session must be fully closed
    // before opening a new one — most Android/iOS camera hardware only
    // allows a single active session at a time, so starting the new
    // controller while the previous one is still open throws a
    // CameraException on the new session (confirmed failure mode: the
    // switch button's target camera "not opening" on real devices). The
    // previous code disposed the old controller only *after* the new one
    // successfully initialized, which is backwards.
    final previous = _controller;
    if (mounted) {
      setState(() {
        // Drop the reference before disposing so CameraPreview never holds
        // a disposed controller while we're between cameras.
        _controller = null;
      });
    }
    await previous?.dispose();

    final newController = CameraController(
      description,
      ResolutionPreset.high,
      enableAudio: false,
    );

    try {
      await newController.initialize();
      if (mounted) {
        setState(() {
          _controller = newController;
          _isCameraInitialized = true;
          _isSwitchingCamera = false;
        });
      }
    } catch (e) {
      await newController.dispose();
      if (mounted) {
        setState(() {
          _isSwitchingCamera = false;
          _error = 'Could not start the camera. Please try again.';
        });
      }
    }
  }

  Future<void> _switchCamera() async {
    if (_cameras.length < 2 || _isSwitchingCamera) return;
    setState(() {
      _isSwitchingCamera = true;
      _error = null;
    });
    _selectedCameraIndex = (_selectedCameraIndex + 1) % _cameras.length;
    await _startCamera(_cameras[_selectedCameraIndex]);
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _processFaceImage(String path) async {
    if (!mounted) return;
    setState(() {
      _isProcessing = true;
      _error = null;
    });

    try {
      final remoteData = RemoteDataSource();
      final result = await remoteData.verifyFace(widget.sessionId, path);

      if (result['success'] == true) {
        final decision = (result['decision'] ?? 'CHECK').toString();
        final venueCheck = result['venue_check'] as Map<String, dynamic>? ?? {};
        final isBlacklisted = venueCheck['blacklisted'] == true;
        final incidentCount = (venueCheck['incidents'] as num?)?.toInt() ?? 0;

        // Only real, backend-sourced signals are shown — no fabricated
        // confidence numbers or hand-authored explanation text. The
        // response shape today doesn't include a numeric risk score (see
        // TODO in decision_view.dart), so riskScore is left null.
        final String reason;
        if (isBlacklisted) {
          reason = 'Visitor has an active venue restriction.';
        } else if (decision == 'CHECK') {
          reason = 'Document details need supervisor review.';
        } else {
          reason = 'Face captured and no venue restriction was found.';
        }

        if (mounted) {
          Navigator.of(context).push(
            AppPageRoute.push(
              DecisionView(
                decision: decision,
                reason: reason,
                isBlacklisted: isBlacklisted,
                incidentCount: incidentCount,
                sessionId: widget.sessionId,
                ocrData: widget.ocrData,
              ),
            ),
          );
        }
      } else {
        setState(() {
          _error = result['message'] ?? 'Face verification failed';
          _isProcessing = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          // Face matching runs real ML inference server-side and can
          // legitimately take a while (cold-started model, CPU-only
          // backend) — a timeout isn't the same failure as an actual
          // match/verification error, so it gets its own message.
          final isTimeout = e is DioException &&
              (e.type == DioExceptionType.receiveTimeout ||
                  e.type == DioExceptionType.sendTimeout ||
                  e.type == DioExceptionType.connectionTimeout);
          _error = isTimeout
              ? 'The verification service is taking longer than usual. Please try again.'
              : 'Could not verify identity. Please try again.';
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    try {
      final image = await _controller!.takePicture();
      await _processFaceImage(image.path);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Could not capture photo. Please try again.');
      }
    }
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      await _processFaceImage(image.path);
    }
  }

  @override
  Widget build(BuildContext context) {
    return CameraCaptureScaffold(
      controller: _controller,
      isInitializing: !_isCameraInitialized || _isSwitchingCamera,
      isOvalGuide: true,
      guideWidthFactor: 0.7,
      guideHeightFactor: 0.9,
      instructionText: 'Position face inside the frame',
      errorText: _error,
      currentStep: 3,
      totalSteps: 3,
      stepLabel: 'Face Verification',
      onCapture: _takePicture,
      onPickFromGallery: _pickImage,
      onClose: () => Navigator.pop(context),
      onSwitchCamera: _cameras.length > 1 ? _switchCamera : null,
      isProcessing: _isProcessing,
      processingStatusText: 'Verifying identity…',
    );
  }
}
