import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Branded loading moment — icon badge + small themed spinner, optionally
/// with a status message. Inline (no Scaffold), for dropping inside an
/// existing `AppPage`/screen body rather than a full-screen loading state.
class BrandedLoadingIndicator extends StatelessWidget {
  final String? message;
  final IconData icon;

  const BrandedLoadingIndicator({
    super.key,
    this.message,
    this.icon = Icons.verified_user_rounded,
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 56,
            height: 56,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: colors.primarySoft,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(icon, color: colors.primary, size: 28),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2.4,
              color: colors.primary,
            ),
          ),
          if (message != null) ...[
            const SizedBox(height: 14),
            Text(
              message!,
              style: AppTypography.subhead.copyWith(color: colors.muted),
            ),
          ],
        ],
      ),
    );
  }
}
