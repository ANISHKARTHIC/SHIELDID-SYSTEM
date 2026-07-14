import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../config/constants.dart';
import '../models/user.dart';
import '../models/visitor.dart';
import '../models/incident.dart';
import '../models/dashboard_stats.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String? _token;

  void setToken(String? token) {
    _token = token;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<Map<String, dynamic>> _handleResponse(http.Response response) async {
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }
    throw ApiException(body['detail'] ?? 'Request failed', response.statusCode);
  }

  Future<User?> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );
      final data = await _handleResponse(response);
      return User.fromJson(data);
    } catch (e) {
      debugPrint('Login error: $e');
      return null;
    }
  }

  Future<User?> register(String username, String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'email': email, 'password': password}),
      );
      final data = await _handleResponse(response);
      return User.fromJson(data);
    } catch (e) {
      debugPrint('Register error: $e');
      return null;
    }
  }

  Future<List<Visitor>> getVisitors({String? search}) async {
    try {
      final uri = Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/visitors')
          .replace(queryParameters: search != null ? {'search': search} : null);
      final response = await http.get(uri, headers: _headers);
      final data = await _handleResponse(response);
      final list = data['visitors'] as List<dynamic>? ?? data as List<dynamic>? ?? [];
      return list.map((e) => Visitor.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      debugPrint('Get visitors error: $e');
      return [];
    }
  }

  Future<Visitor?> getVisitor(int id) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/visitors/$id'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      return Visitor.fromJson(data);
    } catch (e) {
      debugPrint('Get visitor error: $e');
      return null;
    }
  }

  Future<String?> startSession() async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/session/start'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      return data['session_id'] as String?;
    } catch (e) {
      debugPrint('Start session error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> sessionClassify(String sessionId, File imageFile) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/session/$sessionId/classify'),
      );
      request.files.add(await http.MultipartFile.fromPath('file', imageFile.path));
      if (_token != null) request.headers['Authorization'] = 'Bearer $_token';
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      return await _handleResponse(response);
    } catch (e) {
      debugPrint('Classify error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> sessionOcr(String sessionId, File imageFile) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/session/$sessionId/ocr'),
      );
      request.files.add(await http.MultipartFile.fromPath('file', imageFile.path));
      if (_token != null) request.headers['Authorization'] = 'Bearer $_token';
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      return await _handleResponse(response);
    } catch (e) {
      debugPrint('OCR error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> sessionFaceMatch(String sessionId, File imageFile) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/session/$sessionId/face'),
      );
      request.files.add(await http.MultipartFile.fromPath('file', imageFile.path));
      if (_token != null) request.headers['Authorization'] = 'Bearer $_token';
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      return await _handleResponse(response);
    } catch (e) {
      debugPrint('Face match error: $e');
      return null;
    }
  }

  Future<bool> sessionFinalize(String sessionId, String decision, String? notes) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/session/$sessionId/finalize'),
        headers: _headers,
        body: jsonEncode({'decision': decision, 'notes': notes}),
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Finalize error: $e');
      return false;
    }
  }

  Future<DashboardStats?> getDashboardStats() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/dashboard/stats'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      return DashboardStats.fromJson(data);
    } catch (e) {
      debugPrint('Dashboard stats error: $e');
      return null;
    }
  }

  Future<List<VisitLog>> getVisitLogs({int limit = 20}) async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/visits?limit=$limit'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      final list = data['logs'] as List<dynamic>? ?? data as List<dynamic>? ?? [];
      return list.map((e) => VisitLog.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      debugPrint('Visit logs error: $e');
      return [];
    }
  }

  Future<bool> approveEntry(int visitId) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/visits/$visitId/approve'),
        headers: _headers,
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Approve entry error: $e');
      return false;
    }
  }

  Future<bool> rejectEntry(int visitId, {String? reason}) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/visits/$visitId/reject'),
        headers: _headers,
        body: jsonEncode({'reason': reason ?? 'Rejected by security'}),
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Reject entry error: $e');
      return false;
    }
  }

  Future<List<Incident>> getIncidents() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/incidents'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      final list = data['incidents'] as List<dynamic>? ?? data as List<dynamic>? ?? [];
      return list.map((e) => Incident.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      debugPrint('Get incidents error: $e');
      return [];
    }
  }

  Future<bool> createIncident(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/incidents'),
        headers: _headers,
        body: jsonEncode(data),
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Create incident error: $e');
      return false;
    }
  }

  Future<List<BlacklistEntry>> getBlacklist() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/blacklist'),
        headers: _headers,
      );
      final data = await _handleResponse(response);
      final list = data['blacklist'] as List<dynamic>? ?? data as List<dynamic>? ?? [];
      return list.map((e) => BlacklistEntry.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      debugPrint('Get blacklist error: $e');
      return [];
    }
  }

  Future<bool> addToBlacklist(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/blacklist'),
        headers: _headers,
        body: jsonEncode(data),
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Add blacklist error: $e');
      return false;
    }
  }

  Future<bool> removeFromBlacklist(int id) async {
    try {
      final response = await http.delete(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/blacklist/$id'),
        headers: _headers,
      );
      await _handleResponse(response);
      return true;
    } catch (e) {
      debugPrint('Remove blacklist error: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getProfile() async {
    try {
      final response = await http.get(
        Uri.parse('${AppConstants.baseUrl}${AppConstants.apiPrefix}/auth/profile'),
        headers: _headers,
      );
      return await _handleResponse(response);
    } catch (e) {
      debugPrint('Get profile error: $e');
      return null;
    }
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;
  ApiException(this.message, this.statusCode);
  @override
  String toString() => 'ApiException($statusCode): $message';
}
