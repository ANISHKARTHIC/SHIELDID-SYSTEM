import 'package:shared_preferences/shared_preferences.dart';

const _prefsKey = 'biometric_unlock_enabled';

/// Opt-in flag for gating an already-valid session behind a device-local
/// biometric check. Defaults to disabled — this is a security tool, so the
/// auth flow is never silently weakened without an explicit operator choice.
class BiometricPrefs {
  static Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_prefsKey) ?? false;
  }

  static Future<void> setEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefsKey, enabled);
  }
}
