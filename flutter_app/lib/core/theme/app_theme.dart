import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Light-mode palette — "Refined Minimal": near-white canvas, near-black
/// ink, a single hairline border color, and semantic accents used sparingly.
/// Kept as bare static constants for backward compatibility; new/touched
/// screens should read colors via `context.colors.xxx` instead (theme-aware).
class AppColors {
  static const Color ink = Color(0xFF18181B);
  static const Color muted = Color(0xFF71717A);
  static const Color line = Color(0xFFE4E4E7);
  static const Color canvas = Color(0xFFFAFAFA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceRaised = Color(0xFFF4F4F5);
  static const Color primary = Color(0xFF18181B);
  static const Color primarySoft = Color(0xFFF4F4F5);
  static const Color success = Color(0xFF16A34A);
  static const Color successSoft = Color(0xFFDCFCE7);
  static const Color warning = Color(0xFFEA580C);
  static const Color warningSoft = Color(0xFFFFEDD5);
  static const Color danger = Color(0xFFDC2626);
  static const Color dangerSoft = Color(0xFFFEE2E2);
}

/// Dark-mode palette — near-black canvas (not pure black), near-white ink,
/// hairline dividers rather than cards-on-cards, single white CTA. Semantic
/// accents are brighter than light mode for legibility on a dark background.
class AppColorsDark {
  static const Color ink = Color(0xFFFAFAFA);
  static const Color muted = Color(0xFF71717A);
  static const Color line = Color(0xFF1C1C1F);
  static const Color canvas = Color(0xFF0A0A0B);
  static const Color surface = Color(0xFF0A0A0B);
  static const Color surfaceRaised = Color(0xFF141416);
  static const Color primary = Color(0xFFFAFAFA);
  static const Color primarySoft = Color(0xFF1C1C1F);
  static const Color success = Color(0xFF4ADE80);
  static const Color successSoft = Color(0xFF122A1E);
  static const Color warning = Color(0xFFFB923C);
  static const Color warningSoft = Color(0xFF2B1B10);
  static const Color danger = Color(0xFFF87171);
  static const Color dangerSoft = Color(0xFF2C1618);
}

/// Theme-aware color tokens beyond what [ColorScheme] covers (muted/line/
/// canvas/soft-variants have no direct ColorScheme slot). Registered on both
/// [ThemeData]s via `extensions:`, read via `context.colors`.
class AppColorsExt extends ThemeExtension<AppColorsExt> {
  final Color ink;
  final Color muted;
  final Color line;
  final Color canvas;
  final Color surface;
  final Color surfaceRaised;
  final Color primary;
  final Color primarySoft;
  final Color success;
  final Color successSoft;
  final Color warning;
  final Color warningSoft;
  final Color danger;
  final Color dangerSoft;
  final Color onPrimary;

  const AppColorsExt({
    required this.ink,
    required this.muted,
    required this.line,
    required this.canvas,
    required this.surface,
    required this.surfaceRaised,
    required this.primary,
    required this.primarySoft,
    required this.success,
    required this.successSoft,
    required this.warning,
    required this.warningSoft,
    required this.danger,
    required this.dangerSoft,
    required this.onPrimary,
  });

  static const light = AppColorsExt(
    ink: AppColors.ink,
    muted: AppColors.muted,
    line: AppColors.line,
    canvas: AppColors.canvas,
    surface: AppColors.surface,
    surfaceRaised: AppColors.surfaceRaised,
    primary: AppColors.primary,
    primarySoft: AppColors.primarySoft,
    success: AppColors.success,
    successSoft: AppColors.successSoft,
    warning: AppColors.warning,
    warningSoft: AppColors.warningSoft,
    danger: AppColors.danger,
    dangerSoft: AppColors.dangerSoft,
    onPrimary: Colors.white,
  );

  static const dark = AppColorsExt(
    ink: AppColorsDark.ink,
    muted: AppColorsDark.muted,
    line: AppColorsDark.line,
    canvas: AppColorsDark.canvas,
    surface: AppColorsDark.surface,
    surfaceRaised: AppColorsDark.surfaceRaised,
    primary: AppColorsDark.primary,
    primarySoft: AppColorsDark.primarySoft,
    success: AppColorsDark.success,
    successSoft: AppColorsDark.successSoft,
    warning: AppColorsDark.warning,
    warningSoft: AppColorsDark.warningSoft,
    danger: AppColorsDark.danger,
    dangerSoft: AppColorsDark.dangerSoft,
    onPrimary: Color(0xFF0A0A0B),
  );

  @override
  AppColorsExt copyWith({
    Color? ink,
    Color? muted,
    Color? line,
    Color? canvas,
    Color? surface,
    Color? surfaceRaised,
    Color? primary,
    Color? primarySoft,
    Color? success,
    Color? successSoft,
    Color? warning,
    Color? warningSoft,
    Color? danger,
    Color? dangerSoft,
    Color? onPrimary,
  }) {
    return AppColorsExt(
      ink: ink ?? this.ink,
      muted: muted ?? this.muted,
      line: line ?? this.line,
      canvas: canvas ?? this.canvas,
      surface: surface ?? this.surface,
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      primary: primary ?? this.primary,
      primarySoft: primarySoft ?? this.primarySoft,
      success: success ?? this.success,
      successSoft: successSoft ?? this.successSoft,
      warning: warning ?? this.warning,
      warningSoft: warningSoft ?? this.warningSoft,
      danger: danger ?? this.danger,
      dangerSoft: dangerSoft ?? this.dangerSoft,
      onPrimary: onPrimary ?? this.onPrimary,
    );
  }

  @override
  AppColorsExt lerp(ThemeExtension<AppColorsExt>? other, double t) {
    if (other is! AppColorsExt) return this;
    return AppColorsExt(
      ink: Color.lerp(ink, other.ink, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      line: Color.lerp(line, other.line, t)!,
      canvas: Color.lerp(canvas, other.canvas, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      primary: Color.lerp(primary, other.primary, t)!,
      primarySoft: Color.lerp(primarySoft, other.primarySoft, t)!,
      success: Color.lerp(success, other.success, t)!,
      successSoft: Color.lerp(successSoft, other.successSoft, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningSoft: Color.lerp(warningSoft, other.warningSoft, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      dangerSoft: Color.lerp(dangerSoft, other.dangerSoft, t)!,
      onPrimary: Color.lerp(onPrimary, other.onPrimary, t)!,
    );
  }
}

extension AppColorsX on BuildContext {
  AppColorsExt get colors =>
      Theme.of(this).extension<AppColorsExt>() ?? AppColorsExt.light;
}

class AppTheme {
  static ThemeData light() => _build(brightness: Brightness.light, colors: AppColorsExt.light);
  static ThemeData dark() => _build(brightness: Brightness.dark, colors: AppColorsExt.dark);

  static ThemeData _build({
    required Brightness brightness,
    required AppColorsExt colors,
  }) {
    // No custom fontFamily override: '.SF Pro Text' only resolves on iOS
    // (an unguaranteed private system-font name) and silently falls back to
    // Roboto on Android, so the two platforms rendered different type
    // consistently — using each platform's own default is more honest and
    // matches Material 3's built-in cross-platform type ramp.
    final base = ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: colors.ink,
        brightness: brightness,
        surface: colors.surface,
      ),
      useMaterial3: true,
    );

    return base.copyWith(
      extensions: [colors],
      scaffoldBackgroundColor: colors.canvas,
      appBarTheme: AppBarTheme(
        backgroundColor: colors.canvas,
        foregroundColor: colors.ink,
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: TextStyle(
          color: colors.ink,
          fontSize: 20,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.01,
        ),
      ),
      cardTheme: CardThemeData(
        color: colors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: colors.line),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colors.surfaceRaised,
        labelStyle: TextStyle(color: colors.muted),
        floatingLabelStyle: TextStyle(
          color: colors.ink,
          fontWeight: FontWeight.w700,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colors.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colors.ink, width: 1.4),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colors.danger),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colors.primary,
          foregroundColor: colors.onPrimary,
          disabledBackgroundColor: colors.primary.withValues(alpha: 0.35),
          elevation: 0,
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          side: BorderSide(color: colors.line),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: colors.surfaceRaised,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: colors.line),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: colors.canvas,
        indicatorColor: Colors.transparent,
        elevation: 0,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            color: states.contains(WidgetState.selected)
                ? colors.ink
                : colors.muted,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? colors.ink
                : colors.muted,
          ),
        ),
      ),
      dividerTheme: DividerThemeData(color: colors.line, thickness: 1, space: 1),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? colors.onPrimary : colors.muted,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? colors.primary : colors.line,
        ),
        trackOutlineColor: const WidgetStatePropertyAll(Colors.transparent),
      ),
    );
  }
}

class AppPage extends StatelessWidget {
  final String title;
  final String? subtitle;
  final List<Widget>? actions;
  final Widget child;

  const AppPage({
    super.key,
    required this.title,
    this.subtitle,
    this.actions,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: subtitle == null ? 60 : 78,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.01,
                color: colors.ink,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 3),
              Text(
                subtitle!,
                style: TextStyle(
                  color: colors.muted,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ],
        ),
        actions: actions,
      ),
      body: SafeArea(child: child),
    );
  }
}

class AppSurface extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const AppSurface({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(18),
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.line),
      ),
      child: child,
    );
  }
}

class StatusPill extends StatelessWidget {
  final String label;
  final Color color;
  final IconData? icon;

  const StatusPill({
    super.key,
    required this.label,
    required this.color,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 5),
          ] else ...[
            Container(
              width: 6,
              height: 6,
              margin: const EdgeInsets.only(right: 6),
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
          ],
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.02,
            ),
          ),
        ],
      ),
    );
  }
}

IconData platformChevron(BuildContext context) {
  return Theme.of(context).platform == TargetPlatform.iOS
      ? CupertinoIcons.chevron_forward
      : Icons.chevron_right_rounded;
}
