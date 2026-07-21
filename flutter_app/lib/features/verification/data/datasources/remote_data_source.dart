import 'package:dio/dio.dart';
import '../../../../core/network/dio_client.dart';

class RemoteDataSource {
  final Dio _dio = DioClient().dio;

  Future<String> startSession() async {
    final response = await _dio.post('/session/start');
    return response.data['session_id'];
  }

  Future<Map<String, dynamic>> getStats() async {
    final response = await _dio.get('/operator/stats');
    return response.data;
  }

  Future<Map<String, dynamic>> classifyDocument(String sessionId, String imagePath) async {
    final file = await MultipartFile.fromFile(imagePath, filename: 'id.jpg');
    final formData = FormData.fromMap({'file': file});
    
    final response = await _dio.post('/session/$sessionId/classify', data: formData);
    return response.data;
  }

  Future<Map<String, dynamic>> extractOCR(String sessionId, String imagePath) async {
    final file = await MultipartFile.fromFile(imagePath, filename: 'id.jpg');
    final formData = FormData.fromMap({'file': file});
    
    final response = await _dio.post('/session/$sessionId/ocr', data: formData);
    return response.data;
  }

  Future<Map<String, dynamic>> verifyFace(String sessionId, String faceImagePath) async {
    final file = await MultipartFile.fromFile(faceImagePath, filename: 'face.jpg');
    final formData = FormData.fromMap({'file': file});
    
    final response = await _dio.post('/session/$sessionId/face', data: formData);
    return response.data;
  }

  Future<Map<String, dynamic>> submitDecision(String sessionId, String decision, String notes, Map<String, String> ocrData) async {
    final payload = {
      'ocr_name': ocrData['ocr_name'] ?? '',
      'ocr_dob': ocrData['ocr_dob'] ?? '',
      'ocr_address': ocrData['ocr_address'] ?? 'NOT LEGIBLE',
      'doc_number': ocrData['doc_number'] ?? 'NOT LEGIBLE',
      'doc_type': ocrData['doc_type'] ?? 'driving_licence',
      'expiry_date': ocrData['expiry_date'] ?? 'NOT LEGIBLE',
      'issue_date': ocrData['issue_date'] ?? 'NOT LEGIBLE',
      'ocr_confidence': double.tryParse(ocrData['ocr_confidence'] ?? '0.9') ?? 0.9,
      'quality_score': 1.0,
      'authenticity_score': 1.0,
      'risk_score': 1.0,
      'ai_recommendation': 'PASS',
      'staff_decision': decision.toLowerCase(),
      'notes': notes,
    };
    
    final response = await _dio.post(
      '/session/$sessionId/finalize',
      data: payload,
    );
    return response.data;
  }

  Future<List<dynamic>> getHistory() async {
    final response = await _dio.get('/sessions/history');
    return response.data as List<dynamic>;
  }

  Future<List<dynamic>> getNotifications() async {
    final response = await _dio.get('/notifications');
    return response.data as List<dynamic>;
  }
}
