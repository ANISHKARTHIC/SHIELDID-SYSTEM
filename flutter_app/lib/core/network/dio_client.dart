import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../config.dart';
import '../security/token_storage.dart';

/// Callback invoked when the server rejects the stored token (401), so the
/// app can drop the user back to the login screen instead of surfacing a
/// confusing raw network error.
typedef OnSessionExpired = void Function();

class DioClient {
  static final DioClient _instance = DioClient._internal();
  late Dio dio;
  OnSessionExpired? onSessionExpired;

  factory DioClient() {
    return _instance;
  }

  DioClient._internal() {
    dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.defaultBaseUrl,
        // Connecting shouldn't take long even on a slow box, but a
        // t3.micro deployment's AI service can be swap-thrashing its
        // model weights back in after any idle period, so a generous
        // margin here avoids a false "can't connect" on a host that's
        // simply slow to accept the TCP connection under memory pressure.
        connectTimeout: const Duration(seconds: 30),
        // Covers ordinary JSON endpoints (login, stats, history,
        // notifications, etc). classifyDocument/extractOCR/verifyFace in
        // RemoteDataSource override this per-call — the backend itself
        // allows up to 180s for those three since they're the ones that
        // actually invoke AI inference.
        receiveTimeout: const Duration(seconds: 30),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await TokenStorage.readToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            await TokenStorage.clear();
            onSessionExpired?.call();
          }
          handler.next(error);
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
          // /operator/stats itself is cheap (no AI involved), but on a
          // t3.micro deployment the backend process can still be slow to
          // respond under memory pressure from ai-service — 5s was tight
          // enough to report "can't connect" on a backend that was really
          // just momentarily slow.
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );
      final response = await tempDio.get('$targetUrl/operator/stats');
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
