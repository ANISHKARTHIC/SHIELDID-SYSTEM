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
  final VoidCallback? onSwitchCamera;

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
    this.onSwitchCamera,
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
      // errorText is checked even while "initializing"/controller-less:
      // a camera that fails to start (first load, or a failed switch)
      // previously fell straight through to this branch's plain spinner
      // forever, with no close button and no way out — the caller had to
      // be mid-error internally to escape, since this branch never looked
      // at errorText at all. Now a failure shows the same close button
      // and error banner as the ready state, and offers Upload from
      // Gallery as a fallback so the operator isn't blocked entirely.
      final hasError = widget.errorText != null;
      return Scaffold(
        backgroundColor: Colors.black,
        body: SafeArea(
          child: Column(
            children: [
              Align(
                alignment: Alignment.topLeft,
                child: IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 28),
                  onPressed: widget.onClose,
                ),
              ),
              Expanded(
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: (hasError ? context.colors.danger : Colors.white)
                                .withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Icon(
                            hasError
                                ? Icons.error_outline_rounded
                                : Icons.camera_alt_rounded,
                            color: hasError ? context.colors.danger : Colors.white,
                            size: 26,
                          ),
                        ),
                        const SizedBox(height: 20),
                        if (!hasError) ...[
                          const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.4,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 14),
                          const Text(
                            'Starting camera…',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ] else ...[
                          Text(
                            widget.errorText!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 20),
                          OutlinedButton.icon(
                            onPressed: () {
                              HapticFeedback.selectionClick();
                              widget.onPickFromGallery();
                            },
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.white,
                              side: const BorderSide(color: Colors.white38),
                            ),
                            icon: const Icon(Icons.photo_library),
                            label: const Text('Upload from Gallery'),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
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
                        _CircleIconButton(
                          icon: Icons.close_rounded,
                          tooltip: 'Close',
                          diameter: 44,
                          iconSize: 22,
                          onPressed: widget.onClose,
                        )
                      else
                        const SizedBox(width: 44),
                      Expanded(
                        child: VerifyStepIndicator(
                          currentStep: widget.currentStep,
                          totalSteps: widget.totalSteps,
                          label: widget.stepLabel,
                          activeColor: Colors.white,
                        ),
                      ),
                      if (widget.onSwitchCamera != null && !widget.isProcessing)
                        _CircleIconButton(
                          icon: Icons.cameraswitch_rounded,
                          tooltip: 'Switch camera',
                          diameter: 44,
                          iconSize: 20,
                          onPressed: () {
                            HapticFeedback.selectionClick();
                            widget.onSwitchCamera!();
                          },
                        )
                      else
                        const SizedBox(width: 44),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(100),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: context.colors.success,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            widget.instructionText,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
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
                        border: Border.all(
                          color: context.colors.danger.withValues(alpha: 0.6),
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.error_outline_rounded,
                            color: context.colors.danger,
                            size: 20,
                          ),
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

          // Bottom controls: the shutter is pinned to the true horizontal
          // center via Stack + Center (not affected by anything else in
          // the row), and the gallery button is positioned independently
          // relative to the screen edge. The previous Row-based layout
          // paired an Align(centerRight)-wrapped gallery button on the
          // left with an unaligned bare SizedBox spacer on the right —
          // those aren't equivalent, so the shutter was visibly off-center
          // (shifted toward the gallery side) instead of centered.
          if (!widget.isProcessing)
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 28),
                child: SizedBox(
                  height: 76,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      GestureDetector(
                        onTap: _handleCapture,
                        child: Container(
                          width: 76,
                          height: 76,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 4),
                          ),
                          child: Container(
                            width: 60,
                            height: 60,
                            decoration: const BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      Positioned(
                        left: 32,
                        child: _CircleIconButton(
                          icon: Icons.photo_library_rounded,
                          tooltip: 'Upload from Gallery',
                          onPressed: () {
                            HapticFeedback.selectionClick();
                            widget.onPickFromGallery();
                          },
                        ),
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
                          style: TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w700,
                          ),
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

/// A softly-backed circular icon button used for the top-bar (close,
/// switch camera) and bottom-bar (upload from gallery) controls —
/// replaces plain unbacked IconButtons with a filled circle so each reads
/// as a tappable control against the live camera preview instead of a
/// bare icon with poor contrast on bright backgrounds.
class _CircleIconButton extends StatelessWidget {
  /// Default diameter, also used as the balancing spacer's width in the
  /// bottom control row so the shutter button stays visually centered.
  static const double defaultDiameter = 52;

  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;
  final double diameter;
  final double iconSize;

  const _CircleIconButton({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
    this.diameter = defaultDiameter,
    this.iconSize = 24,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.white.withValues(alpha: 0.16),
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onPressed,
          child: SizedBox(
            width: diameter,
            height: diameter,
            child: Icon(icon, color: Colors.white, size: iconSize),
          ),
        ),
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

class _PulsingTextState extends State<_PulsingText>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _opacity = Tween<double>(
      begin: 1.0,
      end: 0.6,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
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
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
