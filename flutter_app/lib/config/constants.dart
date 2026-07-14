class AppConstants {
  static const String appName = 'Pub Entry';
  static const String baseUrl = 'http://192.168.10.10:8000';
  static const String aiServiceUrl = 'http://192.168.10.10:8001';
  static const String apiPrefix = '/api/v1';

  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  static const int minAgeForEntry = 18;
  static const int maxAgeForEntry = 120;

  static const String appVersion = '1.0.0';
}
