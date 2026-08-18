import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Light-mode palette. Kept as bare static constants for backward
/// compatibility with screens not yet migrated to [AppColorsX] — new/touched
/// screens should read colors via `context.colors.xxx` instead, which is
/// theme-aware (light vs dark).
class AppColors {
  static const Color ink = Color(0xFF172033);
  static const Color muted = Color(0xFF667085);
  static const Color line = Color(0xFFE4E7EC);
  static const Color canvas = Color(0xFFF8FAFC);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceRaised = Color(0xFFF1F4F8);
  static const Color primary = Color(0xFF2563EB);
  static const Color primarySoft = Color(0xFFEFF6FF);
  static const Color success = Color(0xFF039855);
  static const Color successSoft = Color(0xFFECFDF3);
  static const Color warning = Color(0xFFF79009);
  static const Color warningSoft = Color(0xFFFFFAEB);
  static const Color danger = Color(0xFFD92D20);
  static const Color dangerSoft = Color(0xFFFEF3F2);
}

/// Dark-mode palette — a deep blue-slate scale rather than pure black/white,
/// so shadows/elevation still read and text doesn't cause halation. Hues
/// match the light palette for brand consistency but are brighter/more
/// saturated where needed for legibility on a dark background.
class AppColorsDark {
  static const Color ink = Color(0xFFF1F5F9);
  static const Color muted = Color(0xFF94A3B8);
  static const Color line = Color(0xFF2A3547);
  static const Color canvas = Color(0xFF0B1220);
  static const Color surface = Color(0xFF141B2C);
  static const Color surfaceRaised = Color(0xFF1B2438);
  static const Color primary = Color(0xFF3B82F6);
  static const Color primarySoft = Color(0xFF17233D);
  static const Color success = Color(0xFF22C55E);
  static const Color successSoft = Color(0xFF122A1E);
  static const Color warning = Color(0xFFF59E0B);
  static const Color warningSoft = Color(0xFF2B2211);
  static const Color danger = Color(0xFFEF4444);
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
    final base = ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: colors.primary,
        brightness: brightness,
        surface: colors.surface,
      ),
      useMaterial3: true,
      fontFamily: '.SF Pro Text',
    );

    // No BoxShadow-based elevation in dark mode — shadows are barely
    // visible on a dark canvas. Card separation is carried by the border
    // instead, matching Material's tint-based dark elevation convention.
    final cardBorder = brightness == Brightness.dark
        ? BorderSide(color: colors.line, width: 1)
        : BorderSide(color: colors.line);

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
          fontSize: 22,
          fontWeight: FontWeight.w800,
        ),
      ),
      cardTheme: CardThemeData(
        color: colors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: cardBorder,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colors.surface,
        labelStyle: TextStyle(color: colors.muted),
        floatingLabelStyle: TextStyle(
          color: colors.primary,
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
          borderSide: BorderSide(color: colors.primary, width: 1.4),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colors.danger),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colors.primary,
          foregroundColor: Colors.white,
          disabledBackgroundColor: colors.primary.withValues(alpha: 0.35),
          elevation: 0,
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: colors.surfaceRaised,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: colors.surface,
        indicatorColor: colors.primarySoft,
        elevation: 0,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            color: states.contains(WidgetState.selected)
                ? colors.primary
                : colors.muted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? colors.primary
                : colors.muted,
          ),
        ),
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
        toolbarHeight: subtitle == null ? 64 : 82,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(title),
            if (subtitle != null) ...[
              const SizedBox(height: 3),
              Text(
                subtitle!,
                style: TextStyle(
                  color: colors.muted,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: colors.line),
        // Shadows read as nothing on a dark canvas, so elevation there is
        // carried by the border/surface-tint alone instead.
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: const Color(0xFF101828).withValues(alpha: 0.04),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
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
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 5),
          ],
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w800,
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
