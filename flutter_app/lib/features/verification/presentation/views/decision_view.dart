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

class _DecisionOutcome {
  final Color top;
  final Color bottom;
  final IconData icon;
  final String label;
  final Color panelBg;

  const _DecisionOutcome({
    required this.top,
    required this.bottom,
    required this.icon,
    required this.label,
    required this.panelBg,
  });
}

class _DecisionViewState extends State<DecisionView>
    with SingleTickerProviderStateMixin {
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

    final reduceMotion = WidgetsBinding
        .instance
        .platformDispatcher
        .accessibilityFeatures
        .disableAnimations;

    _revealController = AnimationController(
      vsync: this,
      duration: reduceMotion
          ? Duration.zero
          : const Duration(milliseconds: 950),
    );

    _iconScale =
        TweenSequence<double>([
          TweenSequenceItem(tween: Tween(begin: 0.6, end: 1.05), weight: 65),
          TweenSequenceItem(tween: Tween(begin: 1.05, end: 1.0), weight: 35),
        ]).animate(
          CurvedAnimation(
            parent: _revealController,
            curve: const Interval(0.0, 0.26, curve: Curves.easeOutBack),
          ),
        );
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

  Future<void> _confirmAndSubmit(
    String finalDecision, {
    bool isDestructiveOverride = false,
  }) async {
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
        showAppErrorSnackBar(
          context,
          'Could not record decision. Please try again.',
        );
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

  _DecisionOutcome _outcomeFor(String decision) {
    switch (decision) {
      case 'BLOCKED':
        return const _DecisionOutcome(
          top: Color(0xFFDC2626),
          bottom: Color(0xFFB91C1C),
          icon: Icons.block_rounded,
          label: 'Blocked',
          panelBg: Color(0x29000000),
        );
      case 'DENY':
        return const _DecisionOutcome(
          top: Color(0xFFDC2626),
          bottom: Color(0xFFB91C1C),
          icon: Icons.cancel_rounded,
          label: 'Deny',
          panelBg: Color(0x29000000),
        );
      case 'PASS':
        return const _DecisionOutcome(
          top: Color(0xFF16A34A),
          bottom: Color(0xFF15803D),
          icon: Icons.check_rounded,
          label: 'Allow',
          panelBg: Color(0x1AFFFFFF),
        );
      case 'CHECK':
      default:
        return const _DecisionOutcome(
          top: Color(0xFFEA580C),
          bottom: Color(0xFFC2410C),
          icon: Icons.priority_high_rounded,
          label: 'Check',
          panelBg: Color(0x24000000),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final outcome = _outcomeFor(widget.decision);

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
                decoration: BoxDecoration(
                  color: colors.successSoft,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.check_rounded,
                  color: colors.success,
                  size: 40,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Decision recorded',
                style: TextStyle(
                  color: colors.ink,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [outcome.top, outcome.bottom],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 4,
                ),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(
                        Icons.close_rounded,
                        color: Colors.white,
                      ),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(28, 8, 28, 20),
                  child: AnimatedBuilder(
                    animation: _revealController,
                    builder: (context, _) {
                      return Column(
                        children: [
                          const SizedBox(height: 12),
                          Opacity(
                            opacity: _iconOpacity.value,
                            child: Transform.scale(
                              scale: _iconScale.value,
                              child: Container(
                                width: 104,
                                height: 104,
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.18),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  outcome.icon,
                                  size: 54,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 22),
                          Opacity(
                            opacity: _labelSlide.value,
                            child: Transform.translate(
                              offset: Offset(0, (1 - _labelSlide.value) * 8),
                              child: Text(
                                outcome.label,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  fontSize: 44,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.02,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Opacity(
                            opacity: _reasonOpacity.value,
                            child: Text(
                              widget.reason,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.85),
                                fontSize: 14,
                                height: 1.4,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                          const SizedBox(height: 26),
                          Opacity(
                            opacity: _detailsSlide.value,
                            child: Transform.translate(
                              offset: Offset(0, (1 - _detailsSlide.value) * 12),
                              child: Container(
                                width: double.infinity,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 18,
                                ),
                                decoration: BoxDecoration(
                                  color: outcome.panelBg,
                                  borderRadius: BorderRadius.circular(18),
                                ),
                                child: Column(
                                  children: [
                                    _buildDetailRow(
                                      'Age',
                                      _calculateAge(widget.ocrData['ocr_dob']),
                                    ),
                                    Divider(
                                      color: Colors.white.withValues(
                                        alpha: 0.16,
                                      ),
                                      height: 1,
                                    ),
                                    if (widget.riskScore != null) ...[
                                      _buildDetailRow(
                                        'Risk Score',
                                        '${(widget.riskScore! * 100).clamp(0, 100).toInt()}%',
                                      ),
                                      Divider(
                                        color: Colors.white.withValues(
                                          alpha: 0.16,
                                        ),
                                        height: 1,
                                      ),
                                    ],
                                    _buildDetailRow(
                                      'Venue Status',
                                      widget.isBlacklisted
                                          ? 'Restricted'
                                          : 'Clear',
                                    ),
                                    if (widget.incidentCount > 0) ...[
                                      Divider(
                                        color: Colors.white.withValues(
                                          alpha: 0.16,
                                        ),
                                        height: 1,
                                      ),
                                      _buildDetailRow(
                                        'Prior Incidents',
                                        widget.incidentCount.toString(),
                                      ),
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
                              child: _buildActions(outcome),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActions(_DecisionOutcome outcome) {
    final enabled = _actionsEnabled && !_isSubmitting;

    if (widget.decision == 'BLOCKED') {
      return SizedBox(
        width: double.infinity,
        height: 58,
        child: OutlinedButton(
          onPressed: enabled
              ? () => _confirmAndSubmit('BLOCK', isDestructiveOverride: true)
              : null,
          style: OutlinedButton.styleFrom(
            side: BorderSide(
              color: Colors.white.withValues(alpha: 0.45),
              width: 1.4,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
          ),
          child: _isSubmitting
              ? const SizedBox(
                  height: 22,
                  width: 22,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.4,
                  ),
                )
              : const Text(
                  'Dismiss Restricted Entry',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
        ),
      );
    }

    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 56,
            child: OutlinedButton(
              onPressed: enabled ? () => _confirmAndSubmit('BLOCK') : null,
              style: OutlinedButton.styleFrom(
                side: BorderSide(
                  color: Colors.white.withValues(alpha: 0.4),
                  width: 1.4,
                ),
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
                        color: Colors.white,
                      ),
                    )
                  : Text(
                      widget.decision == 'CHECK' ? 'Deny' : 'Restrict',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        fontSize: 15,
                      ),
                    ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: SizedBox(
            height: 56,
            child: ElevatedButton(
              onPressed: enabled ? () => _confirmAndSubmit('PASS') : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: outcome.bottom,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: _isSubmitting
                  ? SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(
                        color: outcome.bottom,
                        strokeWidth: 2.4,
                      ),
                    )
                  : Text(
                      widget.decision == 'CHECK' ? 'Approve' : 'Allow',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                      ),
                    ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.75),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
