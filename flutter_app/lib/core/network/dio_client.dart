import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../config.dart';

class DioClient {
  static final DioClient _instance = DioClient._internal();
  late Dio dio;

  factory DioClient() {
    return _instance;
  }

  DioClient._internal() {
    dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.defaultBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.add(
      LogInterceptor(
        request: true,
        requestHeader: true,
        requestBody: true,
        responseHeader: true,
        responseBody: true,
        error: true,
      ),
    );
  }

  Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString('backend_base_url');
      if (savedUrl != null && savedUrl.isNotEmpty) {
        dio.options.baseUrl = savedUrl;
      } else {
        dio.options.baseUrl = AppConfig.defaultBaseUrl;
      }
    } catch (e) {
      dio.options.baseUrl = AppConfig.defaultBaseUrl;
    }
  }

  Future<void> updateBaseUrl(String url) async {
    final cleanUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    dio.options.baseUrl = cleanUrl;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('backend_base_url', cleanUrl);
    } catch (e) {
      // Ignore
    }
  }

  Future<bool> testConnection([String? testUrl]) async {
    try {
      final targetUrl = testUrl ?? dio.options.baseUrl;
      final tempDio = Dio(
        BaseOptions(
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );
      final response = await tempDio.get('$targetUrl/operator/stats');
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
