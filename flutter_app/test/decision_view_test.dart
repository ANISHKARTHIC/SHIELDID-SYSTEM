import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:venuepass_app/core/theme/app_theme.dart';
import 'package:venuepass_app/features/verification/presentation/views/decision_view.dart';

void main() {
  testWidgets('DecisionView shows the fully-revealed end state immediately when reduce-motion is on', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: DecisionView(
            decision: 'PASS',
            reason: 'No venue restriction found.',
            sessionId: 'test-session',
            ocrData: const {'ocr_dob': '1995-01-01'},
          ),
        ),
      ),
    );

    // A single pump (no pumpAndSettle) should already show the end state
    // since disableAnimations forces the reveal controller straight to 1.0.
    await tester.pump();

    expect(find.text('Allow'), findsWidgets);
    expect(find.text('No venue restriction found.'), findsOneWidget);
  });

  testWidgets('DecisionView omits Risk Score row when riskScore is null', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: DecisionView(
            decision: 'CHECK',
            reason: 'Document details need supervisor review.',
            sessionId: 'test-session',
            ocrData: const {},
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Risk Score'), findsNothing);
    expect(find.text('Venue Status'), findsOneWidget);
  });
}
