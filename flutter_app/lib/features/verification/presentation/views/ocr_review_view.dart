import 'package:flutter/material.dart';
import 'face_capture_view.dart';
import 'dart:io';

import '../../data/datasources/remote_data_source.dart';
import '../../../../core/theme/app_theme.dart';

class OCRReviewView extends StatefulWidget {
  final String imagePath;
  final String sessionId;

  const OCRReviewView({
    super.key,
    required this.imagePath,
    required this.sessionId,
  });

  @override
  State<OCRReviewView> createState() => _OCRReviewViewState();
}

class _OCRReviewViewState extends State<OCRReviewView> {
  // Extracted data
  final TextEditingController _surnameController = TextEditingController();
  final TextEditingController _firstNameController = TextEditingController();
  final TextEditingController _dobController = TextEditingController();
  final TextEditingController _licenceController = TextEditingController();

  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _processDocument();
  }

  Future<void> _processDocument() async {
    try {
      final remoteData = RemoteDataSource();
      // 1. Classify
      final classifyResult = await remoteData.classifyDocument(
        widget.sessionId,
        widget.imagePath,
      );

      if (classifyResult['success'] == false) {
        if (mounted) {
          setState(() {
            _error =
                classifyResult['message'] ??
                'Document rejected by AI (Not a valid ID).';
            _isLoading = false;
          });
        }
        return;
      }

      // 2. OCR
      final result = await remoteData.extractOCR(
        widget.sessionId,
        widget.imagePath,
      );

      final extracted = result['extracted_data'];
      if (mounted) {
        setState(() {
          // easy_ocr_provider returns {"name": "...", "dob": "...", "document_number": "..."}
          final fullName = extracted['name'] ?? '';
          final parts = fullName.split(' ');

          _surnameController.text = parts.length > 1 ? parts.last : fullName;
          _firstNameController.text = parts.length > 1
              ? parts.sublist(0, parts.length - 1).join(' ')
              : '';
          _dobController.text = extracted['dob'] ?? '';
          _licenceController.text = extracted['document_number'] ?? '';
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _surnameController.dispose();
    _firstNameController.dispose();
    _dobController.dispose();
    _licenceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Review Details')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? _ErrorState(message: _error!)
          : SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: AspectRatio(
                      aspectRatio: 1.58,
                      child: Image.file(
                        File(widget.imagePath),
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Confirm extracted identity data before continuing.',
                    style: TextStyle(
                      color: AppColors.muted,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 18),
                  _buildEditableField('Surname', _surnameController),
                  const SizedBox(height: 16),
                  _buildEditableField('First Name', _firstNameController),
                  const SizedBox(height: 16),
                  _buildEditableField('Date of Birth', _dobController),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    'Licence Number',
                    _licenceController,
                    isLowConfidence: true,
                  ),
                  const SizedBox(height: 40),
                  ElevatedButton(
                    onPressed: () {
                      // Gather OCR data to pass to next stage
                      final ocrData = {
                        'ocr_name':
                            '${_firstNameController.text} ${_surnameController.text}'
                                .trim(),
                        'ocr_dob': _dobController.text,
                        'ocr_address': 'NOT LEGIBLE',
                        'doc_number': _licenceController.text,
                        'doc_type': 'driving_licence_or_passport',
                        'expiry_date': 'NOT LEGIBLE',
                        'issue_date': 'NOT LEGIBLE',
                        'ocr_confidence': '0.9', // Hardcoded fallback if needed
                      };

                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(
                          builder: (_) => FaceCaptureView(
                            sessionId: widget.sessionId,
                            ocrData: ocrData,
                          ),
                        ),
                      );
                    },
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.face_retouching_natural_rounded),
                        SizedBox(width: 10),
                        Text('Confirm and Capture Face'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildEditableField(
    String label,
    TextEditingController controller, {
    bool isLowConfidence = false,
  }) {
    return TextField(
      controller: controller,
      style: TextStyle(
        color: isLowConfidence ? AppColors.warning : AppColors.ink,
        fontSize: 17,
        fontWeight: FontWeight.w700,
      ),
      decoration: InputDecoration(
        labelText: label,
        suffixIcon: isLowConfidence
            ? const Icon(Icons.warning_amber_rounded, color: AppColors.warning)
            : null,
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;

  const _ErrorState({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: AppSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline_rounded,
                color: AppColors.danger,
                size: 42,
              ),
              const SizedBox(height: 12),
              const Text(
                'Document review failed',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.ink,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
