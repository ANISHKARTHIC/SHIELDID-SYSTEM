import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/empty_state.dart';

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
        const Center(child: CircularProgressIndicator()),
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
      content = ListView.builder(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        itemCount: _history.length,
        itemBuilder: (context, index) {
          final item = _history[index];
          final decision = (item['final_decision'] ?? 'pending').toString();
          final statusColor = _statusColor(decision, colors);
          final statusIcon = _statusIcon(decision);

          DateTime date =
              DateTime.tryParse(item['created_at'] ?? '') ?? DateTime.now();
          String formattedDate = DateFormat('MMM d, yyyy - HH:mm').format(date);

          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: AppSurface(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(statusIcon, color: statusColor),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          formattedDate,
                          style: TextStyle(
                            color: colors.ink,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Session ${item['session_id'].toString().substring(0, 8)}',
                          style: TextStyle(
                            color: colors.muted,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
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
            setState(() => _isLoading = true);
            _fetchHistory();
          },
        ),
      ],
      child: RefreshIndicator(
        onRefresh: _fetchHistory,
        child: content,
      ),
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
