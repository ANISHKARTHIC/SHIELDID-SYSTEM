import 'package:local_auth/local_auth.dart';

/// Thin wrapper around [LocalAuthentication] so screens never import the
/// plugin directly, matching this codebase's existing thin-service pattern
/// (RemoteDataSource, TokenStorage).
class BiometricAuthService {
  static final LocalAuthentication _auth = LocalAuthentication();

  /// Whether this device supports and has biometrics enrolled right now.
  static Future<bool> isAvailable() async {
    try {
      final supported = await _auth.isDeviceSupported();
      if (!supported) return false;
      final canCheck = await _auth.canCheckBiometrics;
      if (!canCheck) return false;
      final available = await _auth.getAvailableBiometrics();
      return available.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  /// Prompts the platform biometric UI. Returns false (never throws) on
  /// cancellation, failure, or any plugin error — callers must treat a
  /// false result as "fall back to password," not as a soft pass.
  static Future<bool> authenticate({required String reason}) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        biometricOnly: true,
        persistAcrossBackgrounding: true,
      );
    } catch (_) {
      return false;
    }
  }
}
