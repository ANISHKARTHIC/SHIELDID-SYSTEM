import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pub_entry_app/core/theme/app_theme.dart';
import 'package:pub_entry_app/core/widgets/empty_state.dart';
import 'package:pub_entry_app/core/widgets/verify_step_indicator.dart';

void main() {
  for (final mode in [Brightness.light, Brightness.dark]) {
    testWidgets('AppSurface renders without exceptions in ${mode.name} mode', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: mode == Brightness.light ? AppTheme.light() : AppTheme.dark(),
          home: const Scaffold(
            body: AppSurface(child: Text('hello')),
          ),
        ),
      );
      expect(find.text('hello'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('EmptyState renders without exceptions in ${mode.name} mode', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: mode == Brightness.light ? AppTheme.light() : AppTheme.dark(),
          home: Scaffold(
            body: Builder(
              builder: (context) => EmptyState(
                icon: Icons.info_outline,
                title: 'Title',
                message: 'Message',
                color: context.colors.primary,
              ),
            ),
          ),
        ),
      );
      expect(find.text('Title'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('VerifyStepIndicator renders without exceptions in ${mode.name} mode', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: mode == Brightness.light ? AppTheme.light() : AppTheme.dark(),
          home: const Scaffold(
            body: VerifyStepIndicator(currentStep: 2, totalSteps: 3, label: 'Review'),
          ),
        ),
      );
      expect(find.textContaining('Step 2 of 3'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('context.colors falls back to light palette without a registered extension', (tester) async {
    late AppColorsExt colors;
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(useMaterial3: true), // no AppColorsExt registered
        home: Builder(
          builder: (context) {
            colors = context.colors;
            return const SizedBox();
          },
        ),
      ),
    );
    expect(colors.canvas, AppColors.canvas);
  });
}
