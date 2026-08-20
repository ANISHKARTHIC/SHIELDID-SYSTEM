class AppConfig {
  /// Real deployed backend (t3.micro free-tier demo — see the repo root
  /// README's "Production Deployment" section). This is the out-of-box
  /// default so installing the app just works without anyone needing to
  /// open Server Configuration first.
  ///
  /// For local development against a backend on your own machine, open
  /// Server Configuration in the app (home screen) and enter your
  /// machine's address instead — e.g. `http://10.0.2.2:8000/api/v1` on the
  /// Android emulator, or `http://your-LAN-IP:8000/api/v1` on a physical
  /// device, matching start_backend.sh. DioClient persists that override
  /// in SharedPreferences, so it's a one-time setup per install.
  static const String defaultBaseUrl =
      'https://venuepass-api.duckdns.org/api/v1';
}
