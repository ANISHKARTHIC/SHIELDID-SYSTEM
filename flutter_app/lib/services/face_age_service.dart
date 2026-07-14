import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import '../config/constants.dart';
import 'api_service.dart';

class FaceAgeService {
  static final FaceAgeService _instance = FaceAgeService._internal();
  factory FaceAgeService() => _instance;
  FaceAgeService._internal();

  final _picker = ImagePicker();
  final _api = ApiService();

  File? _capturedImage;
  Map<String, dynamic>? _result;

  File? get capturedImage => _capturedImage;
  Map<String, dynamic>? get result => _result;

  Future<File?> pickFromGallery() async {
    final xFile = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 1024);
    if (xFile != null) {
      _capturedImage = File(xFile.path);
      return _capturedImage;
    }
    return null;
  }

  Future<File?> captureFromCamera() async {
    final xFile = await _picker.pickImage(source: ImageSource.camera, maxWidth: 1024);
    if (xFile != null) {
      _capturedImage = File(xFile.path);
      return _capturedImage;
    }
    return null;
  }

  Future<Map<String, dynamic>?> verifyAge() async {
    if (_capturedImage == null) return null;
    final result = await _api.verifyFaceAge(_capturedImage!);
    _result = result;
    return result;
  }

  Future<Map<String, dynamic>?> verifyAgeWithMLKit(Uint8List imageBytes) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConstants.aiServiceUrl}/verify/face-age-ml'),
        headers: {'Content-Type': 'application/octet-stream'},
        body: imageBytes,
      );
      if (response.statusCode == 200) {
        _result = jsonDecode(response.body) as Map<String, dynamic>;
        return _result;
      }
    } catch (e) {
      debugPrint('ML Kit face age error: $e');
    }
    return null;
  }

  void clear() {
    _capturedImage = null;
    _result = null;
  }
}
