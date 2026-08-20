import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Themed error snackbar — icon+message on a danger-tinted surface, matching
/// the inline error box pattern already used on the login screen. Replaces
/// several ad-hoc `ScaffoldMessenger` calls with raw non-token colors.
void showAppErrorSnackBar(BuildContext context, String message) {
  final colors = context.colors;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Row(
        children: [
          Icon(Icons.error_outline_rounded, color: colors.danger, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: colors.ink, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      backgroundColor: colors.dangerSoft,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
  );
}

void showAppSuccessSnackBar(BuildContext context, String message) {
  final colors = context.colors;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Row(
        children: [
          Icon(
            Icons.check_circle_outline_rounded,
            color: colors.success,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: colors.ink, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
      backgroundColor: colors.successSoft,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
  );
}
