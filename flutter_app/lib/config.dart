import 'dart:io';
import 'package:flutter/foundation.dart';

class AppConfig {
  /// Machine's primary LAN IP for physical device connection
  static const String physicalDeviceHost = '192.168.1.55';

  /// Dynamic default backend host:
  /// - Android Emulator: 10.0.2.2
  /// - Physical Device (Default): 192.168.1.55
  /// - iOS Simulator / Web / Desktop: 127.0.0.1 / localhost
  static String get defaultBackendHost {
    if (kIsWeb) return 'localhost';
    try {
      if (Platform.isAndroid) {
        // Use physical device host by default for real phones
        return physicalDeviceHost;
      }
    } catch (_) {}
    return physicalDeviceHost;
  }

  static const int backendPort = 8000;
  static const String apiPrefix = '/api/v1';

  static String get defaultBaseUrl =>
      'http://$defaultBackendHost:$backendPort$apiPrefix';
}
