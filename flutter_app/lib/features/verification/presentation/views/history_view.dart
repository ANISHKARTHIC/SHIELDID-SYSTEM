import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';

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
    Widget content;
    if (_isLoading) {
      content = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      content = _EmptyState(
        icon: Icons.error_outline_rounded,
        title: 'History unavailable',
        message: _error!,
        color: AppColors.danger,
      );
    } else if (_history.isEmpty) {
      content = const _EmptyState(
        icon: Icons.history_rounded,
        title: 'No checks yet',
        message: 'Completed verifications will appear here.',
        color: AppColors.primary,
      );
    } else {
      content = ListView.builder(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        itemCount: _history.length,
        itemBuilder: (context, index) {
          final item = _history[index];
          final decision = (item['final_decision'] ?? 'pending').toString();
          final isPass = decision == 'pass';
          final statusColor = isPass ? AppColors.success : AppColors.danger;

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
                    child: Icon(
                      isPass
                          ? Icons.check_rounded
                          : Icons.warning_amber_rounded,
                      color: statusColor,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Session ${item['session_id'].toString().substring(0, 8)}',
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          formattedDate,
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 13,
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
      child: content,
    );
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;
  final Color color;

  const _EmptyState({
    required this.icon,
    required this.title,
    required this.message,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(icon, color: color, size: 30),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.ink,
                fontSize: 20,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
