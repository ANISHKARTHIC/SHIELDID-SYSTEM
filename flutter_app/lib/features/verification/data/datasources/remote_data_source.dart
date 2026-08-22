import 'package:dio/dio.dart';
import '../../../../core/network/dio_client.dart';

class RemoteDataSource {
  final Dio _dio = DioClient().dio;

  /// classify/ocr/face-match all run real CPU-bound ML inference
  /// (EasyOCR/InsightFace) server-side — the backend itself allows up to
  /// 180s for each of these when calling ai-service (v1_router.py), but
  /// the shared DioClient default is only 15s (tuned for fast JSON
  /// endpoints). A cold-start EasyOCR model load, or just slower CPU-only
  /// inference — especially on a t3.micro deployment where the ai-service
  /// can be slow to respond while its model weights page back in from
  /// swap after any idle period — can easily exceed 15s without being a
  /// real failure. These three calls get their own longer receive timeout
  /// (190s, just past the backend's own 180s budget so the backend's own
  /// timeout fires first) to match; every other (fast) endpoint keeps the
  /// shared client's 15s default.
  static const _inferenceTimeout = Duration(seconds: 190);

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post(
      '/auth/login',
      data: {'username': email, 'password': password},
    );
    return response.data;
  }

  /// Backend readiness (database/redis/AI service connectivity), used to
  /// drive the Home screen's real system-status rows. `/ready` lives at the
  /// app root, not under the `/api/v1` prefix the main Dio client uses.
  Future<Map<String, dynamic>> getReadiness() async {
    final apiBaseUrl = _dio.options.baseUrl;
    final rootUrl = apiBaseUrl.replaceFirst(RegExp(r'/api/v1/?$'), '');
    final response = await Dio(
      BaseOptions(
        // The backend's own ai_service probe inside /ready uses a 5s
        // timeout (backend/main.py), plus its own connect/response time on
        // top — 10s here gives that a realistic chance to complete rather
        // than the client giving up first on a t3.micro under load.
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ),
    ).get('$rootUrl/ready');
    return response.data as Map<String, dynamic>;
  }

  Future<String> startSession() async {
    final response = await _dio.post('/session/start');
    return response.data['session_id'];
  }

  Future<Map<String, dynamic>> getStats() async {
    final response = await _dio.get('/operator/stats');
    return response.data;
  }

  /// Combines the classify and OCR steps into a single upload — the photo
  /// used to be sent twice as two sequential requests (classify, then
  /// OCR), each a full network round-trip plus its own server-side
  /// inference pass. Since OCR's document-type routing comes directly
  /// from classify's own result, there's no real reason that had to be
  /// two separate client round-trips; the backend now does both in one
  /// call (backend/api/v1_router.py's /scan endpoint). Response shape
  /// matches the old /ocr endpoint's ({success, extracted_data,
  /// validation}), with success:false + message for a rejected document
  /// (matching the old /classify rejection shape) when the document isn't
  /// a valid ID.
  Future<Map<String, dynamic>> scanDocument(
    String sessionId,
    String imagePath,
  ) async {
    final file = await MultipartFile.fromFile(imagePath, filename: 'id.jpg');
    final formData = FormData.fromMap({'file': file});

    final response = await _dio.post(
      '/session/$sessionId/scan',
      data: formData,
      options: Options(receiveTimeout: _inferenceTimeout, sendTimeout: _inferenceTimeout),
    );
    return response.data;
  }

  Future<Map<String, dynamic>> verifyFace(
    String sessionId,
    String faceImagePath,
  ) async {
    final file = await MultipartFile.fromFile(
      faceImagePath,
      filename: 'face.jpg',
    );
    final formData = FormData.fromMap({'file': file});

    final response = await _dio.post(
      '/session/$sessionId/face',
      data: formData,
      options: Options(receiveTimeout: _inferenceTimeout, sendTimeout: _inferenceTimeout),
    );
    return response.data;
  }

  /// Finalizes the session with the operator's decision. The backend derives
  /// the customer record (name/DOB/document number) from the OCR data it
  /// already stored server-side during the /ocr step — it does not read any
  /// OCR fields from this request body, so only the operator's own decision
  /// and notes are sent.
  Future<Map<String, dynamic>> submitDecision(
    String sessionId,
    String decision,
    String notes,
  ) async {
    final payload = {'staff_decision': decision.toLowerCase(), 'notes': notes};

    final response = await _dio.post(
      '/session/$sessionId/finalize',
      data: payload,
    );
    return response.data;
  }

  Future<List<dynamic>> getHistory({int? limit}) async {
    final response = await _dio.get(
      '/sessions/history',
      queryParameters: limit != null ? {'limit': limit} : null,
    );
    return response.data as List<dynamic>;
  }

  Future<List<dynamic>> getNotifications() async {
    final response = await _dio.get('/notifications');
    return response.data as List<dynamic>;
  }

  Future<List<dynamic>> getCurrentOccupants() async {
    final response = await _dio.get('/occupancy/current');
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> getOccupancyCount() async {
    final response = await _dio.get('/occupancy/count');
    return response.data as Map<String, dynamic>;
  }

  Future<void> checkOutOccupant(int occupancyId) async {
    await _dio.post('/occupancy/$occupancyId/checkout');
  }

  Future<Map<String, dynamic>> createBan(int customerId, String reason) async {
    final response = await _dio.post(
      '/blacklist',
      data: {'customer_id': customerId, 'reason': reason},
    );
    return response.data as Map<String, dynamic>;
  }
}
