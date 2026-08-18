import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'features/verification/presentation/views/home_view.dart';
import 'features/verification/presentation/views/history_view.dart';
import 'features/verification/presentation/views/notifications_view.dart';
import 'features/verification/presentation/views/login_view.dart';
import 'features/verification/presentation/views/profile_view.dart';
import 'core/network/dio_client.dart';
import 'core/security/token_storage.dart';
import 'core/security/biometric_auth_service.dart';
import 'core/security/biometric_prefs.dart';
import 'core/providers/theme_mode_provider.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DioClient().init();
  runApp(const ProviderScope(child: PubEntryApp()));
}

class PubEntryApp extends ConsumerWidget {
  final bool loadInitialData;

  const PubEntryApp({super.key, this.loadInitialData = true});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);
    return MaterialApp(
      title: 'VenuePass',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: themeMode,
      home: AuthGate(loadInitialData: loadInitialData),
    );
  }
}

enum _GateStage { checkingSession, awaitingBiometric, loggedOut, loggedIn }

/// Shows the login screen until a valid token is present, then the main app.
/// If the operator opted into biometric unlock, an already-valid token is
/// re-gated behind a device-local biometric check before the app is shown.
/// Also listens for 401 responses (expired/invalid session) and drops the
/// operator back to login rather than surfacing a confusing network error.
class AuthGate extends StatefulWidget {
  final bool loadInitialData;

  const AuthGate({super.key, this.loadInitialData = true});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  _GateStage _stage = _GateStage.checkingSession;

  @override
  void initState() {
    super.initState();
    DioClient().onSessionExpired = () {
      if (mounted) setState(() => _stage = _GateStage.loggedOut);
    };
    _checkExistingSession();
  }

  Future<void> _checkExistingSession() async {
    String? token;
    try {
      token = await TokenStorage.readToken();
    } catch (e) {
      // A corrupted secure-storage entry (e.g. an Android auto-backup
      // restored the encrypted prefs file without its Keystore-bound key)
      // throws here rather than returning null. Treat it the same as "no
      // token" instead of leaving the gate stuck on checkingSession forever.
      debugPrint('TokenStorage.readToken() failed: $e');
      token = null;
    }
    final hasToken = token != null && token.isNotEmpty;

    if (!hasToken) {
      setState(() => _stage = _GateStage.loggedOut);
      return;
    }

    final biometricEnabled = await BiometricPrefs.isEnabled();
    if (!biometricEnabled) {
      setState(() => _stage = _GateStage.loggedIn);
      return;
    }

    setState(() => _stage = _GateStage.awaitingBiometric);
    await _runBiometricGate();
  }

  Future<void> _runBiometricGate() async {
    final available = await BiometricAuthService.isAvailable();
    if (!available) {
      // Biometrics were enabled previously but are no longer available on
      // this device (e.g. unenrolled) — fall through to the valid token
      // rather than locking the operator out entirely.
      if (mounted) setState(() => _stage = _GateStage.loggedIn);
      return;
    }

    final success = await BiometricAuthService.authenticate(
      reason: 'Unlock VenuePass',
    );

    if (!mounted) return;

    if (success) {
      setState(() => _stage = _GateStage.loggedIn);
    } else {
      // Fail-safe: never silently admit on a failed/cancelled biometric
      // check. Fall back to password login; the stored token is left
      // intact since it is still valid — only the device-local gate wasn't
      // satisfied.
      setState(() => _stage = _GateStage.loggedOut);
    }
  }

  @override
  Widget build(BuildContext context) {
    final Widget content;
    switch (_stage) {
      case _GateStage.checkingSession:
        content = const _BrandedLoadingScreen(key: ValueKey('checking'));
        break;
      case _GateStage.awaitingBiometric:
        content = const _BrandedLoadingScreen(
          key: ValueKey('biometric'),
          message: 'Waiting for biometric unlock…',
        );
        break;
      case _GateStage.loggedOut:
        content = LoginView(
          key: const ValueKey('login'),
          onLoginSuccess: () => setState(() => _stage = _GateStage.loggedIn),
        );
        break;
      case _GateStage.loggedIn:
        content = MainNavigationScreen(
          key: const ValueKey('main'),
          loadInitialData: widget.loadInitialData,
          onLoggedOut: () => setState(() => _stage = _GateStage.loggedOut),
        );
        break;
    }

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 350),
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      transitionBuilder: (child, animation) =>
          FadeTransition(opacity: animation, child: child),
      child: content,
    );
  }
}

class _BrandedLoadingScreen extends StatelessWidget {
  final String? message;

  const _BrandedLoadingScreen({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      backgroundColor: colors.canvas,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: colors.primarySoft,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(
                Icons.verified_user_rounded,
                color: colors.primary,
                size: 32,
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.4,
                color: colors.primary,
              ),
            ),
            if (message != null) ...[
              const SizedBox(height: 16),
              Text(
                message!,
                style: TextStyle(color: colors.muted, fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  final bool loadInitialData;
  final VoidCallback onLoggedOut;

  const MainNavigationScreen({
    super.key,
    this.loadInitialData = true,
    required this.onLoggedOut,
  });

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  late final List<Widget> _screens = [
    HomeView(loadInitialData: widget.loadInitialData),
    const HistoryView(),
    const NotificationsView(),
    ProfileView(onLoggedOut: widget.onLoggedOut),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 200),
        child: KeyedSubtree(
          key: ValueKey(_currentIndex),
          child: _screens[_currentIndex],
        ),
      ),
      bottomNavigationBar: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: context.colors.line)),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) =>
              setState(() => _currentIndex = index),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.verified_user_outlined),
              selectedIcon: Icon(Icons.verified_user),
              label: 'Verify',
            ),
            NavigationDestination(
              icon: Icon(Icons.history_rounded),
              label: 'History',
            ),
            NavigationDestination(
              icon: Icon(Icons.notifications_none_rounded),
              selectedIcon: Icon(Icons.notifications_rounded),
              label: 'Alerts',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}
