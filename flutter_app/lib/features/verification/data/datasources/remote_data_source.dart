import 'package:dio/dio.dart';
import '../../../../core/network/dio_client.dart';

class RemoteDataSource {
  final Dio _dio = DioClient().dio;

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
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
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

  Future<Map<String, dynamic>> classifyDocument(
    String sessionId,
    String imagePath,
  ) async {
    final file = await MultipartFile.fromFile(imagePath, filename: 'id.jpg');
    final formData = FormData.fromMap({'file': file});

    final response = await _dio.post(
      '/session/$sessionId/classify',
      data: formData,
    );
    return response.data;
  }

  Future<Map<String, dynamic>> extractOCR(
    String sessionId,
    String imagePath,
  ) async {
    final file = await MultipartFile.fromFile(imagePath, filename: 'id.jpg');
    final formData = FormData.fromMap({'file': file});

    final response = await _dio.post('/session/$sessionId/ocr', data: formData);
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
