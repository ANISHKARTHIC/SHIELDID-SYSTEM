import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'auth_token';
  static const _roleKey = 'auth_role';
  static const _emailKey = 'auth_email';

  static Future<void> save({
    required String token,
    required String role,
    required String email,
  }) async {
    await _storage.write(key: _tokenKey, value: token);
    await _storage.write(key: _roleKey, value: role);
    await _storage.write(key: _emailKey, value: email);
  }

  static Future<String?> readToken() => _storage.read(key: _tokenKey);
  static Future<String?> readRole() => _storage.read(key: _roleKey);
  static Future<String?> readEmail() => _storage.read(key: _emailKey);

  static Future<void> clear() async {
    await _storage.delete(key: _tokenKey);
    await _storage.delete(key: _roleKey);
    await _storage.delete(key: _emailKey);
  }
}
