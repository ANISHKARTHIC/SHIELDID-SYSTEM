import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/theme/app_theme.dart';

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
      await remoteData.submitDecision(
        widget.sessionId,
        finalDecision,
        widget.reason,
        widget.ocrData,
      );

      if (mounted) {
        // Pop back to home screen
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  String _calculateAge(String? dobString) {
    if (dobString == null || dobString.isEmpty) {
      return 'N/A';
    }
    try {
      final dob = DateTime.parse(dobString);
      final today = DateTime.now();
      int age = today.year - dob.year;
      if (today.month < dob.month ||
          (today.month == dob.month && today.day < dob.day)) {
        age--;
      }
      return age.toString();
    } catch (e) {
      return 'N/A';
    }
  }

  @override
  Widget build(BuildContext context) {
    Color accentColor;
    Color softColor;
    IconData icon;
    String label;

    switch (widget.decision) {
      case 'BLOCKED':
        accentColor = AppColors.danger;
        softColor = AppColors.dangerSoft;
        icon = Icons.block;
        label = 'Blocked';
        break;
      case 'PASS':
        accentColor = AppColors.success;
        softColor = AppColors.successSoft;
        icon = Icons.check_circle_outline;
        label = 'Allow';
        break;
      case 'DENY':
        accentColor = AppColors.danger;
        softColor = AppColors.dangerSoft;
        icon = Icons.cancel_outlined;
        label = 'Deny';
        break;
      case 'CHECK':
      default:
        accentColor = AppColors.warning;
        softColor = AppColors.warningSoft;
        icon = Icons.warning_amber_outlined;
        label = 'Check';
        break;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Decision')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppSurface(
                padding: const EdgeInsets.all(22),
                child: Column(
                  children: [
                    Container(
                      width: 96,
                      height: 96,
                      decoration: BoxDecoration(
                        color: softColor,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, size: 54, color: accentColor),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      label,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.w900,
                        color: accentColor,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.reason,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 15,
                        height: 1.35,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              AppSurface(
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 8,
                ),
                child: Column(
                  children: [
                    _buildDetailRow(
                      'Age',
                      _calculateAge(widget.ocrData['ocr_dob']),
                    ),
                    const Divider(color: AppColors.line, height: 1),
                    _buildDetailRow(
                      'Risk Score',
                      '${(widget.riskScore * 100).clamp(0, 100).toInt()}%',
                    ),
                    const Divider(color: AppColors.line, height: 1),
                    _buildDetailRow(
                      'Venue Status',
                      widget.decision == 'BLOCKED' ? 'Restricted' : 'Clear',
                    ),
                  ],
                ),
              ),
              const Spacer(),
              if (widget.decision == 'BLOCKED')
                ElevatedButton(
                  onPressed: _isSubmitting
                      ? null
                      : () => _submitDecision('BLOCK'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.danger,
                  ),
                  child: _isSubmitting
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('Dismiss Restricted Entry'),
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _isSubmitting
                            ? null
                            : () => _submitDecision('BLOCK'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.danger,
                          side: const BorderSide(color: AppColors.danger),
                          minimumSize: const Size.fromHeight(56),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text(
                                'Restrict',
                                style: TextStyle(fontWeight: FontWeight.w900),
                              ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isSubmitting
                            ? null
                            : () => _submitDecision('PASS'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.success,
                        ),
                        child: _isSubmitting
                            ? const CircularProgressIndicator(
                                color: Colors.white,
                              )
                            : const Text('Allow'),
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
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 15),
          child: Text(
            label,
            style: const TextStyle(
              color: AppColors.muted,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: AppColors.ink,
            fontSize: 18,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    );
  }
}
