import 'package:flutter/foundation.dart';

class AppConfig {
  /// Machine's primary LAN IP for physical device connection
  static const String physicalDeviceHost = '192.168.1.55';

  /// Dynamic default backend host:
  /// - Web: localhost
  /// - Android, iOS (simulator or physical device), and every other
  ///   platform: physicalDeviceHost (the venue's LAN server address)
  ///
  /// This app is designed to run on a real device on the venue's Wi-Fi
  /// network talking to a real backend on that network — that's the
  /// common case this default should serve, not local-simulator
  /// development. Distinguishing "iOS Simulator" from "real iPhone" isn't
  /// possible from Platform.isIOS alone (both report true) and would
  /// require an extra plugin (device_info_plus) just to special-case a
  /// development-only scenario. The server address is always
  /// user-editable at runtime regardless (Profile > Connection), so a
  /// developer running the Simulator against a localhost backend can
  /// simply set that there.
  static String get defaultBackendHost {
    if (kIsWeb) return 'localhost';
    return physicalDeviceHost;
  }

  static const int backendPort = 8000;
  static const String apiPrefix = '/api/v1';

  static String get defaultBaseUrl =>
      'http://$defaultBackendHost:$backendPort$apiPrefix';
}
