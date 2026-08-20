import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/empty_state.dart';
import '../../../../core/widgets/branded_loading.dart';

class HistoryView extends StatefulWidget {
  const HistoryView({super.key});

  @override
  State<HistoryView> createState() => _HistoryViewState();
}

class _HistoryViewState extends State<HistoryView> {
  bool _isLoading = true;
  List<dynamic> _history = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    try {
      final remoteData = RemoteDataSource();
      final history = await remoteData.getHistory();
      if (mounted) {
        setState(() {
          _history = history;
          _isLoading = false;
          _error = null;
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
  Widget build(BuildContext context) {
    final colors = context.colors;
    Widget content;
    if (_isLoading) {
      content = _scrollableEmptyState(
        const BrandedLoadingIndicator(icon: Icons.history_rounded),
      );
    } else if (_error != null) {
      content = _scrollableEmptyState(
        EmptyState(
          icon: Icons.error_outline_rounded,
          title: 'History unavailable',
          message: _error!,
          color: colors.danger,
        ),
      );
    } else if (_history.isEmpty) {
      content = _scrollableEmptyState(
        EmptyState(
          icon: Icons.history_rounded,
          title: 'No checks yet',
          message: 'Completed verifications will appear here.',
          color: colors.primary,
        ),
      );
    } else {
      content = ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
        itemCount: _history.length,
        separatorBuilder: (context, index) =>
            Divider(color: colors.line, height: 1),
        itemBuilder: (context, index) {
          final item = _history[index];
          final decision = (item['final_decision'] ?? 'pending').toString();
          final statusColor = _statusColor(decision, colors);
          final statusIcon = _statusIcon(decision);

          DateTime date =
              DateTime.tryParse(item['created_at'] ?? '') ?? DateTime.now();
          String formattedDate = DateFormat('MMM d, HH:mm').format(date);

          return TweenAnimationBuilder<double>(
            key: ValueKey(item['session_id']),
            tween: Tween(begin: 0, end: 1),
            duration: Duration(milliseconds: 260 + (index.clamp(0, 8) * 30)),
            curve: Curves.easeOutCubic,
            builder: (context, value, child) => Opacity(
              opacity: value,
              child: Transform.translate(
                offset: Offset(0, (1 - value) * 6),
                child: child,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(statusIcon, color: statusColor, size: 18),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          formattedDate,
                          style: AppTypography.body.copyWith(
                            color: colors.ink,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Session ${item['session_id'].toString().substring(0, 8)}',
                          style: AppTypography.footnote.copyWith(
                            color: colors.muted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  StatusPill(label: decision.toUpperCase(), color: statusColor),
                ],
              ),
            ),
          );
        },
      );
    }

    return AppPage(
      title: 'History',
      subtitle: 'Completed verification sessions',
      actions: [
        IconButton(
          icon: const Icon(Icons.refresh_rounded),
          onPressed: () {
            HapticFeedback.selectionClick();
            setState(() => _isLoading = true);
            _fetchHistory();
          },
        ),
      ],
      child: RefreshIndicator(onRefresh: _fetchHistory, child: content),
    );
  }

  Widget _scrollableEmptyState(Widget child) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: child,
          ),
        );
      },
    );
  }

  Color _statusColor(String decision, AppColorsExt colors) {
    switch (decision) {
      case 'pass':
        return colors.success;
      case 'check':
        return colors.warning;
      case 'deny':
      case 'block':
      case 'blocked':
        return colors.danger;
      default:
        return colors.muted;
    }
  }

  IconData _statusIcon(String decision) {
    switch (decision) {
      case 'pass':
        return Icons.check_rounded;
      case 'check':
        return Icons.help_outline_rounded;
      case 'deny':
      case 'block':
      case 'blocked':
        return Icons.block_rounded;
      default:
        return Icons.schedule_rounded;
    }
  }
}
