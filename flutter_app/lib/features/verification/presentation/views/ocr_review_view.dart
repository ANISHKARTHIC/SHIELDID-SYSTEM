import 'dart:async';
import 'package:flutter/material.dart';
import 'face_capture_view.dart';
import 'dart:io';

import '../../data/datasources/remote_data_source.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/verify_step_indicator.dart';
import '../../../../core/navigation/app_page_route.dart';

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
  final TextEditingController _surnameController = TextEditingController();
  final TextEditingController _firstNameController = TextEditingController();
  final TextEditingController _dobController = TextEditingController();
  final TextEditingController _licenceController = TextEditingController();

  bool _isLoading = true;
  String? _error;

  static const _loadingMessages = [
    'Analyzing document…',
    'Extracting details…',
    'Validating fields…',
  ];
  int _loadingMessageIndex = 0;
  Timer? _loadingTimer;

  @override
  void initState() {
    super.initState();
    _loadingTimer = Timer.periodic(const Duration(milliseconds: 1400), (_) {
      if (mounted) {
        setState(() => _loadingMessageIndex = (_loadingMessageIndex + 1) % _loadingMessages.length);
      }
    });
    _processDocument();
  }

  Future<void> _processDocument() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final remoteData = RemoteDataSource();
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

      final result = await remoteData.extractOCR(
        widget.sessionId,
        widget.imagePath,
      );

      final extracted = result['extracted_data'];
      if (mounted) {
        setState(() {
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
          _error = 'Could not read this document. Please try again.';
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _loadingTimer?.cancel();
    _surnameController.dispose();
    _firstNameController.dispose();
    _dobController.dispose();
    _licenceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Scaffold(
      appBar: AppBar(title: const Text('Review Details')),
      body: _isLoading
          ? _LoadingState(message: _loadingMessages[_loadingMessageIndex])
          : _error != null
          ? _ErrorState(message: _error!, onRetry: _processDocument)
          : SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const VerifyStepIndicator(
                    currentStep: 2,
                    totalSteps: 3,
                    label: 'Review Details',
                  ),
                  const SizedBox(height: 18),
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
                  Text(
                    'Confirm extracted identity data before continuing.',
                    style: TextStyle(
                      color: colors.muted,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 18),
                  _buildEditableField(colors, 'Surname', _surnameController),
                  const SizedBox(height: 16),
                  _buildEditableField(colors, 'First Name', _firstNameController),
                  const SizedBox(height: 16),
                  _buildEditableField(colors, 'Date of Birth', _dobController),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    colors,
                    'Licence Number',
                    _licenceController,
                    isLowConfidence: true,
                  ),
                  const SizedBox(height: 40),
                  ElevatedButton(
                    onPressed: () {
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
                        'ocr_confidence': '0.9',
                      };

                      Navigator.of(context).push(
                        AppPageRoute.push(
                          FaceCaptureView(
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
    AppColorsExt colors,
    String label,
    TextEditingController controller, {
    bool isLowConfidence = false,
  }) {
    return TextField(
      controller: controller,
      style: TextStyle(
        color: isLowConfidence ? colors.warning : colors.ink,
        fontSize: 17,
        fontWeight: FontWeight.w700,
      ),
      decoration: InputDecoration(
        labelText: label,
        suffixIcon: isLowConfidence
            ? Icon(Icons.warning_amber_rounded, color: colors.warning)
            : null,
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  final String message;

  const _LoadingState({required this.message});

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(color: colors.primary),
          const SizedBox(height: 18),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 250),
            child: Text(
              message,
              key: ValueKey(message),
              style: TextStyle(color: colors.muted, fontSize: 14, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: AppSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.error_outline_rounded,
                color: colors.danger,
                size: 42,
              ),
              const SizedBox(height: 12),
              Text(
                'Document review failed',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: colors.ink,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: colors.muted,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
