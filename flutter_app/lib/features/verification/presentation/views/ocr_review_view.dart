import 'package:flutter/material.dart';
import 'decision_view.dart';
import 'dart:io';

class OCRReviewView extends StatefulWidget {
  final String imagePath;
  
  const OCRReviewView({Key? key, required this.imagePath}) : super(key: key);

  @override
  State<OCRReviewView> createState() => _OCRReviewViewState();
}

class _OCRReviewViewState extends State<OCRReviewView> {
  // Mock extracted data
  final TextEditingController _surnameController = TextEditingController(text: 'SMITH');
  final TextEditingController _firstNameController = TextEditingController(text: 'JOHN');
  final TextEditingController _dobController = TextEditingController(text: '1990-05-15');
  final TextEditingController _licenceController = TextEditingController(text: 'SMITH905155J99Z9');

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
      body: SingleChildScrollView(
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
                // In full implementation, save to SQLite and queue for backend sync
                Navigator.push(context, MaterialPageRoute(builder: (_) => const DecisionView(decision: 'PASS', riskScore: 8.5, reason: 'Age verified. No hits.')));
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
