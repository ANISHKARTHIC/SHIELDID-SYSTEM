import 'dart:async';
import 'package:shared_preferences/shared_preferences.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final _alertController = StreamController<Map<String, dynamic>>.broadcast();
  bool _notificationsEnabled = true;

  Stream<Map<String, dynamic>> get alerts => _alertController.stream;
  bool get notificationsEnabled => _notificationsEnabled;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
  }

  void sendAlert(String title, String message, {String? type}) {
    if (!_notificationsEnabled) return;
    _alertController.add({
      'title': title,
      'message': message,
      'type': type ?? 'info',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    _notificationsEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', enabled);
  }

  void dispose() {
    _alertController.close();
  }
}
