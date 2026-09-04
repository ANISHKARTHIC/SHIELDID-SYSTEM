import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Branded launch screen shown while the auth gate checks for an existing
/// session (main.dart's AuthGate) — the moment right after the native
/// splash (flutter_native_splash, a static image) hands off to the first
/// real Flutter frame. Replaces a generic spinner+icon with the actual
/// app logo scaling/fading in, so the native-splash-to-app transition
/// reads as one continuous branded moment instead of a static image
/// abruptly cutting to a plain loading spinner.
class AnimatedSplashScreen extends StatefulWidget {
  final String? message;

  const AnimatedSplashScreen({super.key, this.message});

  @override
  State<AnimatedSplashScreen> createState() => _AnimatedSplashScreenState();
}

class _AnimatedSplashScreenState extends State<AnimatedSplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;
  late final Animation<double> _messageOpacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );

    // Logo overshoots slightly then settles — reads as a confident
    // "arrival" rather than a plain linear fade-in.
    _logoScale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.75, end: 1.06)
            .chain(CurveTween(curve: Curves.easeOutCubic)),
        weight: 70,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.06, end: 1.0)
            .chain(CurveTween(curve: Curves.easeOut)),
        weight: 30,
      ),
    ]).animate(_controller);

    _logoOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
    );

    _messageOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.55, 1.0, curve: Curves.easeOut),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      backgroundColor: colors.canvas,
      body: Center(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Opacity(
                  opacity: _logoOpacity.value,
                  child: Transform.scale(
                    scale: _logoScale.value,
                    child: Image.asset(
                      'assets/branding/logo_transparent_512.png',
                      width: 108,
                      height: 108,
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                Opacity(
                  opacity: _messageOpacity.value,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.4,
                          color: colors.primary,
                        ),
                      ),
                      if (widget.message != null) ...[
                        const SizedBox(height: 16),
                        Text(
                          widget.message!,
                          style: AppTypography.subhead.copyWith(color: colors.muted),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
