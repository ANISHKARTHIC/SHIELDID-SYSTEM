import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';

class DecisionView extends StatefulWidget {
  final String decision;
  final double riskScore;
  final String reason;
  final String sessionId;
  final Map<String, String> ocrData;

  const DecisionView({
    super.key,
    required this.decision,
    required this.riskScore,
    required this.reason,
    required this.sessionId,
    required this.ocrData,
  });

  @override
  State<DecisionView> createState() => _DecisionViewState();
}

class _DecisionViewState extends State<DecisionView> {
  bool _isSubmitting = false;

  Future<void> _submitDecision(String finalDecision) async {
    setState(() {
      _isSubmitting = true;
    });
    
    try {
      final remoteData = RemoteDataSource();
      await remoteData.submitDecision(widget.sessionId, finalDecision, widget.reason, widget.ocrData);
      
      if (mounted) {
        // Pop back to home screen
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    Color bgColor;
    IconData icon;
    
    switch (widget.decision) {
      case 'BLOCKED':
        bgColor = Colors.red[900]!;
        icon = Icons.block;
        break;
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
                widget.decision,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 64, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 40),
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    _buildDetailRow('Age', '34'), // In real app, pass from OCR
                    const SizedBox(height: 16),
                    _buildDetailRow('Risk Score', '${widget.riskScore}'),
                    const SizedBox(height: 16),
                    _buildDetailRow('Blacklist', widget.decision == 'BLOCKED' ? 'BANNED' : 'Clear'),
                    const SizedBox(height: 24),
                    Text(
                      widget.reason,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 18),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              if (widget.decision == 'BLOCKED')
                ElevatedButton(
                  onPressed: _isSubmitting ? null : () => _submitDecision('BLOCK'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.red[900],
                    padding: const EdgeInsets.symmetric(vertical: 24),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  child: _isSubmitting 
                      ? const CircularProgressIndicator() 
                      : const Text('DISMISS (BANNED)', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : () => _submitDecision('BLOCK'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.red[800],
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 24),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        ),
                        child: _isSubmitting 
                            ? const CircularProgressIndicator(color: Colors.white) 
                            : const Text('RESTRICT', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : () => _submitDecision('PASS'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green[700],
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 24),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        ),
                        child: _isSubmitting 
                            ? const CircularProgressIndicator(color: Colors.white) 
                            : const Text('ALLOW', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
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
