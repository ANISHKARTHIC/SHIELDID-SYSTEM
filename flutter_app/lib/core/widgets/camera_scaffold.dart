import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';
import 'scan_guide_frame.dart';
import 'verify_step_indicator.dart';

/// Shared full-screen camera capture scaffold used by both the ID-document
/// and face capture screens. Replaces the duplicated raw black Scaffold +
/// fixed-pixel-offset Positioned layout with a SafeArea-correct layout, a
/// shutter-flash effect, and a themed error banner.
class CameraCaptureScaffold extends StatefulWidget {
  final CameraController? controller;
  final bool isInitializing;
  final bool isOvalGuide;
  final double guideWidthFactor;
  final double guideHeightFactor;
  final String instructionText;
  final String? errorText;
  final int currentStep;
  final int totalSteps;
  final String stepLabel;
  final Future<void> Function() onCapture;
  final VoidCallback onPickFromGallery;
  final VoidCallback onClose;
  final bool isProcessing;
  final String? processingStatusText;
  final VoidCallback? onCancelProcessing;

  const CameraCaptureScaffold({
    super.key,
    required this.controller,
    required this.isInitializing,
    required this.instructionText,
    required this.currentStep,
    required this.totalSteps,
    required this.stepLabel,
    required this.onCapture,
    required this.onPickFromGallery,
    required this.onClose,
    this.isOvalGuide = false,
    this.guideWidthFactor = 0.85,
    this.guideHeightFactor = 0.55,
    this.errorText,
    this.isProcessing = false,
    this.processingStatusText,
    this.onCancelProcessing,
  });

  @override
  State<CameraCaptureScaffold> createState() => _CameraCaptureScaffoldState();
}

class _CameraCaptureScaffoldState extends State<CameraCaptureScaffold> {
  bool _showFlash = false;

  Future<void> _handleCapture() async {
    HapticFeedback.mediumImpact();
    setState(() => _showFlash = true);
    Future.delayed(const Duration(milliseconds: 180), () {
      if (mounted) setState(() => _showFlash = false);
    });
    await widget.onCapture();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.isInitializing || widget.controller == null) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
      );
    }

    final size = MediaQuery.of(context).size;
    final accent = context.colors.primary;

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(widget.controller!),

          // Dim overlay with a cutout for the guide frame.
          ColorFiltered(
            colorFilter: ColorFilter.mode(
              Colors.black.withValues(alpha: 0.6),
              BlendMode.srcOut,
            ),
            child: Stack(
              fit: StackFit.expand,
              children: [
                Container(
                  decoration: const BoxDecoration(
                    color: Colors.black,
                    backgroundBlendMode: BlendMode.dstOut,
                  ),
                ),
                Center(
                  child: Container(
                    width: size.width * widget.guideWidthFactor,
                    height: widget.isOvalGuide
                        ? size.width * widget.guideHeightFactor
                        : size.width * widget.guideHeightFactor,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(
                        widget.isOvalGuide ? 200 : 20,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Animated corner-bracket + scan-line frame, drawn on top of the cutout.
          Center(
            child: ScanGuideFrame(
              width: size.width * widget.guideWidthFactor,
              height: size.width * widget.guideHeightFactor,
              isOval: widget.isOvalGuide,
              accentColor: accent,
              isActive: !widget.isProcessing && !_showFlash,
            ),
          ),

          // Top: close button, step indicator, instructions, error banner.
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      if (!widget.isProcessing)
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.white, size: 28),
                          onPressed: widget.onClose,
                        )
                      else
                        const SizedBox(width: 48),
                      Expanded(
                        child: VerifyStepIndicator(
                          currentStep: widget.currentStep,
                          totalSteps: widget.totalSteps,
                          label: widget.stepLabel,
                          activeColor: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    widget.instructionText,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      shadows: [Shadow(blurRadius: 8, color: Colors.black54)],
                    ),
                  ),
                  if (widget.errorText != null) ...[
                    const SizedBox(height: 14),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.55),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: context.colors.danger.withValues(alpha: 0.6)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.error_outline_rounded, color: context.colors.danger, size: 20),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              widget.errorText!,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Bottom controls.
          if (!widget.isProcessing)
            SafeArea(
              child: Align(
                alignment: Alignment.bottomCenter,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 24),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      const SizedBox(width: 60),
                      GestureDetector(
                        onTap: _handleCapture,
                        child: Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 4),
                            color: Colors.white.withValues(alpha: 0.3),
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: widget.onPickFromGallery,
                        icon: const Icon(
                          Icons.photo_library,
                          color: Colors.white,
                          size: 36,
                        ),
                        tooltip: 'Upload from Gallery',
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Processing overlay.
          if (widget.isProcessing)
            Container(
              color: Colors.black54,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: accent),
                    if (widget.processingStatusText != null) ...[
                      const SizedBox(height: 18),
                      _PulsingText(text: widget.processingStatusText!),
                    ],
                    if (widget.onCancelProcessing != null) ...[
                      const SizedBox(height: 24),
                      TextButton(
                        onPressed: widget.onCancelProcessing,
                        child: const Text(
                          'Cancel',
                          style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),

          // Shutter flash.
          IgnorePointer(
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 90),
              opacity: _showFlash ? 0.85 : 0.0,
              child: Container(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}

class _PulsingText extends StatefulWidget {
  final String text;

  const _PulsingText({required this.text});

  @override
  State<_PulsingText> createState() => _PulsingTextState();
}

class _PulsingTextState extends State<_PulsingText> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _opacity = Tween<double>(begin: 1.0, end: 0.6)
        .animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: Text(
        widget.text,
        textAlign: TextAlign.center,
        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
      ),
    );
  }
}
