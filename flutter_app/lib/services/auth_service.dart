import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';
import 'api_service.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  final _secureStorage = const FlutterSecureStorage();
  final _localAuth = LocalAuthentication();
  final _api = ApiService();

  User? _currentUser;
  bool _isAuthenticated = false;

  User? get currentUser => _currentUser;
  bool get isAuthenticated => _isAuthenticated;

  Future<void> init() async {
    final token = await _secureStorage.read(key: 'auth_token');
    final userData = await _secureStorage.read(key: 'user_data');
    if (token != null && userData != null) {
      _api.setToken(token);
      _currentUser = User.fromJson(jsonDecode(userData));
      _isAuthenticated = true;
    }
  }

  Future<bool> login(String username, String password) async {
    final user = await _api.login(username, password);
    if (user != null) {
      _currentUser = user;
      _isAuthenticated = true;
      if (user.token != null) {
        await _secureStorage.write(key: 'auth_token', value: user.token);
        _api.setToken(user.token);
      }
      await _secureStorage.write(key: 'user_data', value: jsonEncode(user.toJson()));
      return true;
    }
    return false;
  }

  Future<bool> register(String username, String email, String password) async {
    final user = await _api.register(username, email, password);
    if (user != null) {
      _currentUser = user;
      _isAuthenticated = true;
      if (user.token != null) {
        await _secureStorage.write(key: 'auth_token', value: user.token);
        _api.setToken(user.token);
      }
      await _secureStorage.write(key: 'user_data', value: jsonEncode(user.toJson()));
      return true;
    }
    return false;
  }

  Future<bool> hasBiometrics() async {
    try {
      return await _localAuth.canCheckBiometrics || await _localAuth.isDeviceSupported();
    } catch (e) {
      debugPrint('Biometrics check error: $e');
      return false;
    }
  }

  Future<bool> authenticateWithBiometrics() async {
    try {
      return await _localAuth.authenticate(
        localizedReason: 'Authenticate to access Pub Entry',
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
        ),
      );
    } catch (e) {
      debugPrint('Biometric auth error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    _currentUser = null;
    _isAuthenticated = false;
    _api.setToken(null);
    await _secureStorage.delete(key: 'auth_token');
    await _secureStorage.delete(key: 'user_data');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('biometric_enabled', false);
  }

  Future<bool> isFirstLaunch() async {
    final prefs = await SharedPreferences.getInstance();
    return !(prefs.getBool('onboarding_completed') ?? false);
  }

  Future<void> completeOnboarding() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_completed', true);
  }
}
