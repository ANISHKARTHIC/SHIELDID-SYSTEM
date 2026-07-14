import 'dart:io';
import 'package:image_picker/image_picker.dart';
import '../models/visitor.dart';
import 'api_service.dart';

class DocumentScanService {
  static final DocumentScanService _instance = DocumentScanService._internal();
  factory DocumentScanService() => _instance;
  DocumentScanService._internal();

  final _picker = ImagePicker();
  final _api = ApiService();

  File? _capturedDocument;
  ScanResult? _scanResult;

  File? get capturedDocument => _capturedDocument;
  ScanResult? get scanResult => _scanResult;

  Future<File?> pickDocument() async {
    final xFile = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 2048);
    if (xFile != null) {
      _capturedDocument = File(xFile.path);
      return _capturedDocument;
    }
    return null;
  }

  Future<File?> captureDocument() async {
    final xFile = await _picker.pickImage(source: ImageSource.camera, maxWidth: 2048);
    if (xFile != null) {
      _capturedDocument = File(xFile.path);
      return _capturedDocument;
    }
    return null;
  }

  Future<ScanResult?> scan() async {
    if (_capturedDocument == null) return null;
    _scanResult = await _api.scanDocument(_capturedDocument!);
    return _scanResult;
  }

  void clear() {
    _capturedDocument = null;
    _scanResult = null;
  }
}
