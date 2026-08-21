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
  final TextEditingController _addressController = TextEditingController();
  final TextEditingController _issueDateController = TextEditingController();
  final TextEditingController _expiryDateController = TextEditingController();

  bool _isLoading = true;
  String? _error;
  String _documentType = 'unknown';

  // From extracted_data.confidences / validation — used to drive the
  // low-confidence warning icon on fields whose extraction the backend
  // itself wasn't confident about, instead of hardcoding the licence
  // number field to always warn regardless of how the extraction went.
  double? _licenceConfidence;
  bool _licenceValid = true;
  static const _lowConfidenceThreshold = 70.0;

  // Overall document-legitimacy result from the backend's DVLA-formula
  // cross-check (validation.is_valid / validation.errors) — surfaced as a
  // visible pass/fail banner rather than only being available buried in
  // per-field warning icons or the backend log.
  bool _documentValid = true;
  List<String> _validationErrors = [];

  static const _notLegiblePlaceholder = 'NOT LEGIBLE';

  /// The backend returns this literal string when a field couldn't be
  /// extracted — treat it as empty in the editable UI so staff see a blank
  /// field to fill in, not the placeholder text itself.
  String _cleanField(dynamic value) {
    final text = (value ?? '').toString();
    return text == _notLegiblePlaceholder ? '' : text;
  }

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
        setState(
          () => _loadingMessageIndex =
              (_loadingMessageIndex + 1) % _loadingMessages.length,
        );
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
      // uk_driving_licence responses carry surname/first_names already
      // correctly separated server-side (UKDrivingLicenceProcessor spatially
      // parses fields 1/2 independently) — use those directly rather than
      // re-splitting the flattened "name" string by whitespace, which
      // silently mis-attributes multi-word surnames (e.g. "HENRY CHRISTY
      // PAUL") to the first-name field since naive splitting has no way to
      // know where the surname actually ends.
      final fields = extracted['fields'] as Map<String, dynamic>?;
      final confidences = extracted['confidences'] as Map<String, dynamic>?;
      // extracted_data.validation is the DVLA-formula legitimacy check
      // (surname/DOB/initials cross-checked against the licence number
      // itself, from UKDrivingLicenceProcessor) — distinct from the
      // top-level result['validation'], which only checks field
      // completeness and age, not whether the licence number's own
      // encoded data is internally consistent. The legitimacy banner
      // needs the former.
      final licenceValidation =
          extracted['validation'] as Map<String, dynamic>?;
      final validationErrors =
          (licenceValidation?['errors'] as List?)?.cast<String>() ?? [];

      if (mounted) {
        setState(() {
          if (fields != null) {
            _surnameController.text = _cleanField(fields['surname']);
            _firstNameController.text = _cleanField(fields['first_names']);
          } else {
            // Passport / other document types: fall back to the flattened
            // name, which is all the backend returns for those.
            final fullName = extracted['name'] ?? '';
            final parts = fullName.split(' ');
            _surnameController.text = parts.length > 1 ? parts.last : fullName;
            _firstNameController.text = parts.length > 1
                ? parts.sublist(0, parts.length - 1).join(' ')
                : '';
          }
          _dobController.text = extracted['dob'] ?? '';
          _licenceController.text = extracted['document_number'] ?? '';
          _addressController.text = _cleanField(extracted['address']);
          _issueDateController.text = _cleanField(extracted['issue_date']);
          _expiryDateController.text = _cleanField(extracted['expiry_date']);
          _documentType = extracted['document_type'] ?? 'unknown';

          final licenceConf = confidences?['licence_number'];
          _licenceConfidence = licenceConf is num
              ? licenceConf.toDouble()
              : null;
          _licenceValid = validationErrors.every(
            (e) => !e.toLowerCase().contains('licence number') &&
                !e.toLowerCase().contains('mismatch'),
          );

          _documentValid = licenceValidation?['is_valid'] as bool? ?? true;
          _validationErrors = validationErrors;

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
    _addressController.dispose();
    _issueDateController.dispose();
    _expiryDateController.dispose();
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
                  if (_documentType == 'uk_driving_licence')
                    _buildLegitimacyBanner(colors),
                  if (_documentType == 'uk_driving_licence')
                    const SizedBox(height: 14),
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
                  _buildEditableField(
                    colors,
                    'First Name',
                    _firstNameController,
                  ),
                  const SizedBox(height: 16),
                  _buildEditableField(colors, 'Date of Birth', _dobController),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    colors,
                    'Licence Number',
                    _licenceController,
                    isLowConfidence: !_licenceValid ||
                        _licenceController.text.isEmpty ||
                        (_licenceConfidence != null &&
                            _licenceConfidence! < _lowConfidenceThreshold),
                  ),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    colors,
                    'Date of Issue',
                    _issueDateController,
                    isLowConfidence: _issueDateController.text.isEmpty,
                  ),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    colors,
                    'Date of Expiry',
                    _expiryDateController,
                    isLowConfidence: _expiryDateController.text.isEmpty,
                  ),
                  const SizedBox(height: 16),
                  _buildEditableField(
                    colors,
                    'Address',
                    _addressController,
                    isLowConfidence: _addressController.text.isEmpty,
                    maxLines: 2,
                  ),
                  const SizedBox(height: 40),
                  ElevatedButton(
                    onPressed: () {
                      if (_surnameController.text.trim().isEmpty ||
                          _firstNameController.text.trim().isEmpty ||
                          _dobController.text.trim().isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Surname, first name and date of birth are required before continuing.',
                            ),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                        return;
                      }
                      final ocrData = {
                        'ocr_name':
                            '${_firstNameController.text} ${_surnameController.text}'
                                .trim(),
                        'ocr_dob': _dobController.text,
                        'ocr_address': _addressController.text.isNotEmpty
                            ? _addressController.text
                            : 'NOT LEGIBLE',
                        'doc_number': _licenceController.text,
                        'doc_type': _documentType,
                        'expiry_date': _expiryDateController.text.isNotEmpty
                            ? _expiryDateController.text
                            : 'NOT LEGIBLE',
                        'issue_date': _issueDateController.text.isNotEmpty
                            ? _issueDateController.text
                            : 'NOT LEGIBLE',
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

  /// Surfaces the backend's DVLA-formula legitimacy check (surname/DOB/
  /// initials cross-validated against the licence number's own encoded
  /// data) as a visible pass/fail mark, instead of leaving it only
  /// reachable via the per-field warning icon or the backend log.
  Widget _buildLegitimacyBanner(AppColorsExt colors) {
    final bg = _documentValid ? colors.successSoft : colors.dangerSoft;
    final fg = _documentValid ? colors.success : colors.danger;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: fg.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _documentValid
                    ? Icons.verified_rounded
                    : Icons.gpp_bad_rounded,
                color: fg,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                _documentValid
                    ? 'Licence number verified'
                    : 'Licence number could not be verified',
                style: TextStyle(
                  color: fg,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          if (!_documentValid && _validationErrors.isNotEmpty) ...[
            const SizedBox(height: 6),
            ..._validationErrors.map(
              (e) => Padding(
                padding: const EdgeInsets.only(left: 28, top: 2),
                child: Text(
                  e,
                  style: TextStyle(color: fg, fontSize: 12.5),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildEditableField(
    AppColorsExt colors,
    String label,
    TextEditingController controller, {
    bool isLowConfidence = false,
    int maxLines = 1,
  }) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
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
              style: TextStyle(
                color: colors.muted,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
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
              Icon(Icons.error_outline_rounded, color: colors.danger, size: 42),
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
