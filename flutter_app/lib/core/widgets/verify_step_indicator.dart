import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// "Step N of total" progress row for the verification wizard
/// (Document → Review → Face). Decision is the payoff reveal, not counted
/// as an input step.
class VerifyStepIndicator extends StatelessWidget {
  final int currentStep; // 1-based
  final int totalSteps;
  final String label;
  final Color? activeColor;

  const VerifyStepIndicator({
    super.key,
    required this.currentStep,
    required this.totalSteps,
    required this.label,
    this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final accent = activeColor ?? colors.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: List.generate(totalSteps, (i) {
            final stepIndex = i + 1;
            final isDone = stepIndex < currentStep;
            final isCurrent = stepIndex == currentStep;
            final segmentColor = isDone || isCurrent
                ? accent
                : accent.withValues(alpha: 0.25);

            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: stepIndex == totalSteps ? 0 : 6,
                ),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeOut,
                  height: 4,
                  decoration: BoxDecoration(
                    color: segmentColor,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 8),
        Text(
          'Step $currentStep of $totalSteps — $label',
          style: TextStyle(
            color: colors.muted,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
