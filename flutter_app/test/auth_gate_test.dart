import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:venuepass_app/main.dart';
import 'package:venuepass_app/features/verification/presentation/views/login_view.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('AuthGate shows LoginView when no token is stored', (tester) async {
    FlutterSecureStorage.setMockInitialValues({});

    await tester.pumpWidget(
      const ProviderScope(child: PubEntryApp(loadInitialData: false)),
    );
    await tester.pumpAndSettle();

    expect(find.byType(LoginView), findsOneWidget);
  });

  testWidgets('AuthGate shows MainNavigationScreen when a token exists and biometric is off', (tester) async {
    FlutterSecureStorage.setMockInitialValues({
      'auth_token': 'test-token',
      'auth_role': 'door_staff',
      'auth_email': 'operator@venue.test',
    });

    await tester.pumpWidget(
      const ProviderScope(child: PubEntryApp(loadInitialData: false)),
    );
    await tester.pumpAndSettle();

    expect(find.byType(MainNavigationScreen), findsOneWidget);
    expect(find.byType(LoginView), findsNothing);
  });
}
