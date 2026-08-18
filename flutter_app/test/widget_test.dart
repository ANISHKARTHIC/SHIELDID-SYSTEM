import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:venuepass_app/main.dart';

void main() {
  testWidgets('App loads without errors', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: PubEntryApp(loadInitialData: false)),
    );
    expect(find.byType(PubEntryApp), findsOneWidget);
  });
}
