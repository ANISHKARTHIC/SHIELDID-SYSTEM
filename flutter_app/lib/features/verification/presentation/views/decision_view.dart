import 'package:flutter/material.dart';

class DecisionView extends StatelessWidget {
  final String decision;
  final double riskScore;
  final String reason;

  const DecisionView({
    Key? key,
    required this.decision,
    required this.riskScore,
    required this.reason,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color bgColor;
    IconData icon;
    
    switch (decision) {
      case 'PASS':
        bgColor = Colors.green[800]!;
        icon = Icons.check_circle_outline;
        break;
      case 'DENY':
        bgColor = Colors.red[800]!;
        icon = Icons.cancel_outlined;
        break;
      case 'CHECK':
      default:
        bgColor = Colors.orange[800]!;
        icon = Icons.warning_amber_outlined;
        break;
    }

    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(icon, size: 120, color: Colors.white),
              const SizedBox(height: 24),
              Text(
                decision,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 64, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 40),
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    _buildDetailRow('Age', '34'),
                    const SizedBox(height: 16),
                    _buildDetailRow('Risk Score', '$riskScore'),
                    const SizedBox(height: 16),
                    _buildDetailRow('Blacklist', 'Clear'),
                    const SizedBox(height: 24),
                    Text(
                      reason,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 18),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              ElevatedButton(
                onPressed: () {
                  // Pop back to home screen
                  Navigator.of(context).popUntil((route) => route.isFirst);
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: bgColor,
                  padding: const EdgeInsets.symmetric(vertical: 24),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: const Text('DONE', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 18)),
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
