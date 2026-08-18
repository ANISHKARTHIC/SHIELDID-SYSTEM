import 'package:flutter/material.dart';

/// Animated viewfinder guide for the two camera capture screens: a
/// corner-bracket frame (rectangular for ID documents, oval for faces) with
/// a subtle scanning sweep, giving a "security checkpoint terminal" feel
/// instead of a static placeholder rectangle. Built entirely from Flutter
/// primitives (AnimationController + CustomPainter), no external animation
/// assets.
class ScanGuideFrame extends StatefulWidget {
  final double width;
  final double height;
  final bool isOval;
  final Color accentColor;
  final bool isActive; // pauses the sweep during capture/processing

  const ScanGuideFrame({
    super.key,
    required this.width,
    required this.height,
    required this.accentColor,
    this.isOval = false,
    this.isActive = true,
  });

  @override
  State<ScanGuideFrame> createState() => _ScanGuideFrameState();
}

class _ScanGuideFrameState extends State<ScanGuideFrame>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );
    if (widget.isActive) _controller.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(covariant ScanGuideFrame oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isActive != oldWidget.isActive) {
      if (widget.isActive) {
        _controller.repeat(reverse: true);
      } else {
        _controller.stop();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.width,
      height: widget.height,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return CustomPaint(
            painter: _GuideFramePainter(
              isOval: widget.isOval,
              accentColor: widget.accentColor,
              sweepProgress: _controller.value,
            ),
          );
        },
      ),
    );
  }
}

class _GuideFramePainter extends CustomPainter {
  final bool isOval;
  final Color accentColor;
  final double sweepProgress;

  _GuideFramePainter({
    required this.isOval,
    required this.accentColor,
    required this.sweepProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      Radius.circular(isOval ? size.shortestSide / 2 : 20),
    );

    // Outline
    final outlinePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.85)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawRRect(rrect, outlinePaint);

    // Corner brackets (skipped for oval — an oval outline already reads
    // clearly without brackets, and brackets on an oval look visually odd).
    if (!isOval) {
      final bracketPaint = Paint()
        ..color = accentColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.5
        ..strokeCap = StrokeCap.round;
      const armLength = 26.0;
      const inset = 2.0;

      void bracket(Offset corner, Offset dx, Offset dy) {
        canvas.drawLine(corner, corner + dx * armLength, bracketPaint);
        canvas.drawLine(corner, corner + dy * armLength, bracketPaint);
      }

      bracket(Offset(inset, inset), const Offset(1, 0), const Offset(0, 1));
      bracket(Offset(size.width - inset, inset), const Offset(-1, 0), const Offset(0, 1));
      bracket(Offset(inset, size.height - inset), const Offset(1, 0), const Offset(0, -1));
      bracket(
        Offset(size.width - inset, size.height - inset),
        const Offset(-1, 0),
        const Offset(0, -1),
      );
    }

    // Scan-line sweep, clipped to the guide shape.
    canvas.save();
    canvas.clipRRect(rrect);
    final sweepY = size.height * sweepProgress;
    final sweepPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          accentColor.withValues(alpha: 0.0),
          accentColor.withValues(alpha: 0.55),
          accentColor.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromLTWH(0, sweepY - 24, size.width, 48));
    canvas.drawRect(Rect.fromLTWH(0, sweepY - 24, size.width, 48), sweepPaint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _GuideFramePainter oldDelegate) =>
      oldDelegate.sweepProgress != sweepProgress ||
      oldDelegate.accentColor != accentColor ||
      oldDelegate.isOval != isOval;
}
