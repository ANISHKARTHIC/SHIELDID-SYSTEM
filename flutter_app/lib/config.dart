class AppConfig {
  /// Default backend API base URL — the real deployed VenuePass backend,
  /// not a LAN-only address, so the app works out of the box on any
  /// network without per-device/per-venue IP configuration. Still fully
  /// user-editable at runtime (Profile > Connection settings), which is
  /// what venues with their own self-hosted backend should use instead.
  static const String defaultBaseUrl = 'https://venuepass-api.duckdns.org/api/v1';
}
