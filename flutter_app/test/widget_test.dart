import 'package:flutter_test/flutter_test.dart';
import 'package:pub_entry_app/main.dart';

void main() {
  testWidgets('App loads without errors', (WidgetTester tester) async {
    await tester.pumpWidget(const PubEntryApp());
    expect(find.byType(PubEntryApp), findsOneWidget);
  });
}
