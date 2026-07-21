import 'package:flutter/material.dart';
import 'face_capture_view.dart';
import 'dart:io';

import '../../data/datasources/remote_data_source.dart';

class OCRReviewView extends StatefulWidget {
  final String imagePath;
  final String sessionId;
  
  const OCRReviewView({super.key, required this.imagePath, required this.sessionId});

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
      final classifyResult = await remoteData.classifyDocument(widget.sessionId, widget.imagePath);
      
      if (classifyResult['success'] == false) {
        if (mounted) {
          setState(() {
            _error = classifyResult['message'] ?? 'Document rejected by AI (Not a valid ID).';
            _isLoading = false;
          });
        }
        return;
      }

      // 2. OCR
      final result = await remoteData.extractOCR(widget.sessionId, widget.imagePath);
      
      final extracted = result['extracted_data'];
      if (mounted) {
        setState(() {
          // easy_ocr_provider returns {"name": "...", "dob": "...", "document_number": "..."}
          final fullName = extracted['name'] ?? '';
          final parts = fullName.split(' ');
          
          _surnameController.text = parts.length > 1 ? parts.last : fullName;
          _firstNameController.text = parts.length > 1 ? parts.sublist(0, parts.length - 1).join(' ') : '';
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
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Review Details', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.grey[900],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _error != null
            ? Center(child: Text('Error: $_error', style: const TextStyle(color: Colors.red)))
            : SingleChildScrollView(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      height: 200,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        image: DecorationImage(
                          image: FileImage(File(widget.imagePath)),
                          fit: BoxFit.cover,
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    _buildEditableField('Surname', _surnameController),
                    const SizedBox(height: 16),
                    _buildEditableField('First Name', _firstNameController),
                    const SizedBox(height: 16),
                    _buildEditableField('Date of Birth', _dobController),
                    const SizedBox(height: 16),
                    _buildEditableField('Licence Number', _licenceController, isLowConfidence: true),
                    const SizedBox(height: 40),
                    ElevatedButton(
                      onPressed: () {
                        // Gather OCR data to pass to next stage
                        final ocrData = {
                          'ocr_name': '${_firstNameController.text} ${_surnameController.text}'.trim(),
                          'ocr_dob': _dobController.text,
                          'ocr_address': 'NOT LEGIBLE',
                          'doc_number': _licenceController.text,
                          'doc_type': 'driving_licence_or_passport',
                          'expiry_date': 'NOT LEGIBLE',
                          'issue_date': 'NOT LEGIBLE',
                          'ocr_confidence': '0.9', // Hardcoded fallback if needed
                        };
                        
                        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => FaceCaptureView(
                          sessionId: widget.sessionId,
                          ocrData: ocrData,
                        )));
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blueAccent,
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: const Text('CONFIRM & DECIDE', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
                    ),
                  ],
                ),
              ),
    );
  }

  Widget _buildEditableField(String label, TextEditingController controller, {bool isLowConfidence = false}) {
    return TextField(
      controller: controller,
      style: TextStyle(color: isLowConfidence ? Colors.orange : Colors.white, fontSize: 18),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Colors.grey),
        filled: true,
        fillColor: Colors.grey[900],
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Colors.blueAccent)),
        suffixIcon: isLowConfidence ? const Icon(Icons.warning, color: Colors.orange) : null,
      ),
    );
  }
}
