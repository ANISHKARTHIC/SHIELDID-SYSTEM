import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
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
  bool _isCameraInitialized = false;
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

    CameraDescription? frontCamera;
    for (var camera in cameras) {
      if (camera.lensDirection == CameraLensDirection.front) {
        frontCamera = camera;
        break;
      }
    }
    frontCamera ??= cameras.first;

    _controller = CameraController(
      frontCamera,
      ResolutionPreset.high,
      enableAudio: false,
    );

    try {
      await _controller!.initialize();
      if (mounted) setState(() => _isCameraInitialized = true);
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
          _error = 'Could not verify identity. Please try again.';
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
      isInitializing: !_isCameraInitialized,
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
      isProcessing: _isProcessing,
      processingStatusText: 'Verifying identity…',
    );
  }
}
