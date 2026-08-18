import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/app_snackbar.dart';

class DecisionView extends StatefulWidget {
  final String decision;
  // TODO: backend does not expose risk_score/explainability on
  // POST /session/{id}/face today — only {success, decision, venue_check}.
  // Once that response is extended, this can become a real measured score
  // instead of being omitted from display.
  final double? riskScore;
  final String reason;
  final bool isBlacklisted;
  final int incidentCount;
  final String sessionId;
  final Map<String, String> ocrData;

  const DecisionView({
    super.key,
    required this.decision,
    required this.reason,
    required this.sessionId,
    required this.ocrData,
    this.riskScore,
    this.isBlacklisted = false,
    this.incidentCount = 0,
  });

  @override
  State<DecisionView> createState() => _DecisionViewState();
}

class _DecisionViewState extends State<DecisionView> with SingleTickerProviderStateMixin {
  bool _isSubmitting = false;
  bool _decisionRecorded = false;
  late final AnimationController _revealController;
  late final Animation<double> _iconScale;
  late final Animation<double> _iconOpacity;
  late final Animation<double> _labelSlide;
  late final Animation<double> _reasonOpacity;
  late final Animation<double> _detailsSlide;
  late final Animation<double> _actionsSlide;
  bool _actionsEnabled = false;

  @override
  void initState() {
    super.initState();

    final reduceMotion = WidgetsBinding.instance.platformDispatcher.accessibilityFeatures.disableAnimations;

    _revealController = AnimationController(
      vsync: this,
      duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 950),
    );

    _iconScale = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.6, end: 1.05), weight: 65),
      TweenSequenceItem(tween: Tween(begin: 1.05, end: 1.0), weight: 35),
    ]).animate(CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.0, 0.26, curve: Curves.easeOutBack),
    ));
    _iconOpacity = CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.0, 0.2, curve: Curves.easeOut),
    );
    _labelSlide = CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.15, 0.45, curve: Curves.easeOut),
    );
    _reasonOpacity = CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.30, 0.60, curve: Curves.easeOut),
    );
    _detailsSlide = CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.45, 0.75, curve: Curves.easeOut),
    );
    _actionsSlide = CurvedAnimation(
      parent: _revealController,
      curve: const Interval(0.60, 0.90, curve: Curves.easeOut),
    );

    _revealController.addStatusListener((status) {
      if (status == AnimationStatus.completed && mounted) {
        setState(() => _actionsEnabled = true);
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fireOutcomeHaptic();
      if (reduceMotion) {
        _revealController.value = 1.0;
      } else {
        _revealController.forward();
      }
    });
  }

  void _fireOutcomeHaptic() {
    switch (widget.decision) {
      case 'BLOCKED':
      case 'DENY':
        HapticFeedback.heavyImpact();
        break;
      case 'PASS':
        HapticFeedback.mediumImpact();
        break;
      default:
        HapticFeedback.selectionClick();
    }
  }

  @override
  void dispose() {
    _revealController.dispose();
    super.dispose();
  }

  Future<void> _confirmAndSubmit(String finalDecision, {bool isDestructiveOverride = false}) async {
    if (isDestructiveOverride) {
      HapticFeedback.selectionClick();
      final confirmed = await showAppConfirmDialog(
        context,
        title: 'Override restriction?',
        message:
            'This customer has an active venue restriction. Overriding will allow entry and record your decision against this session.',
        confirmLabel: 'Override & Allow',
        isDestructive: true,
        icon: Icons.warning_amber_rounded,
      );
      if (confirmed != true) return;
      HapticFeedback.heavyImpact();
    }
    await _submitDecision(finalDecision);
  }

  Future<void> _submitDecision(String finalDecision) async {
    setState(() => _isSubmitting = true);

    try {
      final remoteData = RemoteDataSource();
      await remoteData.submitDecision(
        widget.sessionId,
        finalDecision,
        widget.reason,
        widget.ocrData,
      );

      if (!mounted) return;
      setState(() {
        _isSubmitting = false;
        _decisionRecorded = true;
      });
      await Future.delayed(const Duration(milliseconds: 650));
      if (mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } catch (e) {
      if (mounted) {
        showAppErrorSnackBar(context, 'Could not record decision. Please try again.');
        setState(() => _isSubmitting = false);
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
    final colors = context.colors;
    Color accentColor;
    Color softColor;
    IconData icon;
    String label;

    switch (widget.decision) {
      case 'BLOCKED':
        accentColor = colors.danger;
        softColor = colors.dangerSoft;
        icon = Icons.block;
        label = 'Blocked';
        break;
      case 'PASS':
        accentColor = colors.success;
        softColor = colors.successSoft;
        icon = Icons.check_circle_outline;
        label = 'Allow';
        break;
      case 'DENY':
        accentColor = colors.danger;
        softColor = colors.dangerSoft;
        icon = Icons.cancel_outlined;
        label = 'Deny';
        break;
      case 'CHECK':
      default:
        accentColor = colors.warning;
        softColor = colors.warningSoft;
        icon = Icons.warning_amber_outlined;
        label = 'Check';
        break;
    }

    if (_decisionRecorded) {
      return Scaffold(
        backgroundColor: colors.canvas,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(color: colors.successSoft, shape: BoxShape.circle),
                child: Icon(Icons.check_rounded, color: colors.success, size: 40),
              ),
              const SizedBox(height: 16),
              Text(
                'Decision recorded',
                style: TextStyle(color: colors.ink, fontSize: 18, fontWeight: FontWeight.w800),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Decision')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: AnimatedBuilder(
            animation: _revealController,
            builder: (context, _) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  AppSurface(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      children: [
                        Opacity(
                          opacity: _iconOpacity.value,
                          child: Transform.scale(
                            scale: _iconScale.value,
                            child: Container(
                              width: 96,
                              height: 96,
                              decoration: BoxDecoration(color: softColor, shape: BoxShape.circle),
                              child: Icon(icon, size: 54, color: accentColor),
                            ),
                          ),
                        ),
                        const SizedBox(height: 18),
                        Opacity(
                          opacity: _labelSlide.value,
                          child: Transform.translate(
                            offset: Offset(0, (1 - _labelSlide.value) * 8),
                            child: Text(
                              label,
                              textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 48, fontWeight: FontWeight.w900, color: accentColor),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Opacity(
                          opacity: _reasonOpacity.value,
                          child: Text(
                            widget.reason,
                            textAlign: TextAlign.center,
                            style: TextStyle(color: colors.muted, fontSize: 15, height: 1.35, fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Opacity(
                    opacity: _detailsSlide.value,
                    child: Transform.translate(
                      offset: Offset(0, (1 - _detailsSlide.value) * 12),
                      child: AppSurface(
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                        child: Column(
                          children: [
                            _buildDetailRow(colors, 'Age', _calculateAge(widget.ocrData['ocr_dob'])),
                            Divider(color: colors.line, height: 1),
                            if (widget.riskScore != null) ...[
                              _buildDetailRow(colors, 'Risk Score', '${(widget.riskScore! * 100).clamp(0, 100).toInt()}%'),
                              Divider(color: colors.line, height: 1),
                            ],
                            _buildDetailRow(
                              colors,
                              'Venue Status',
                              widget.isBlacklisted ? 'Restricted' : 'Clear',
                            ),
                            if (widget.incidentCount > 0) ...[
                              Divider(color: colors.line, height: 1),
                              _buildDetailRow(colors, 'Prior Incidents', widget.incidentCount.toString()),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  Opacity(
                    opacity: _actionsSlide.value,
                    child: Transform.translate(
                      offset: Offset(0, (1 - _actionsSlide.value) * 12),
                      child: _buildActions(colors),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildActions(AppColorsExt colors) {
    final enabled = _actionsEnabled && !_isSubmitting;

    if (widget.decision == 'BLOCKED') {
      return ElevatedButton(
        onPressed: enabled ? () => _confirmAndSubmit('BLOCK', isDestructiveOverride: true) : null,
        style: ElevatedButton.styleFrom(backgroundColor: colors.danger),
        child: _isSubmitting
            ? const SizedBox(
                height: 22,
                width: 22,
                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.4),
              )
            : const Text('Dismiss Restricted Entry'),
      );
    }

    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: enabled ? () => _confirmAndSubmit('BLOCK') : null,
            style: OutlinedButton.styleFrom(
              foregroundColor: colors.danger,
              side: BorderSide(color: colors.danger),
              minimumSize: const Size.fromHeight(56),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: _isSubmitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Restrict', style: TextStyle(fontWeight: FontWeight.w900)),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton(
            onPressed: enabled ? () => _confirmAndSubmit('PASS') : null,
            style: ElevatedButton.styleFrom(backgroundColor: colors.success),
            child: _isSubmitting
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.4),
                  )
                : const Text('Allow'),
          ),
        ),
      ],
    );
  }

  Widget _buildDetailRow(AppColorsExt colors, String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 15),
          child: Text(
            label,
            style: TextStyle(color: colors.muted, fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
        Text(
          value,
          style: TextStyle(color: colors.ink, fontSize: 18, fontWeight: FontWeight.w900),
        ),
      ],
    );
  }
}
