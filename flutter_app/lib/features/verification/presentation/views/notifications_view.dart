import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';

class NotificationsView extends StatefulWidget {
  const NotificationsView({super.key});

  @override
  State<NotificationsView> createState() => _NotificationsViewState();
}

class _NotificationsViewState extends State<NotificationsView> {
  bool _isLoading = true;
  List<dynamic> _notifications = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
  }

  Future<void> _fetchNotifications() async {
    try {
      final remoteData = RemoteDataSource();
      final notifications = await remoteData.getNotifications();
      if (mounted) {
        setState(() {
          _notifications = notifications;
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
        title: 'Alerts unavailable',
        message: _error!,
        color: AppColors.danger,
      );
    } else if (_notifications.isEmpty) {
      content = const _EmptyState(
        icon: Icons.notifications_none_rounded,
        title: 'No new alerts',
        message: 'Flagged sessions and supervisor messages will appear here.',
        color: AppColors.primary,
      );
    } else {
      content = ListView.builder(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        itemCount: _notifications.length,
        itemBuilder: (context, index) {
          final notif = _notifications[index];
          final isAlert = notif['type'] == 'ALERT';
          final color = isAlert ? AppColors.danger : AppColors.primary;

          DateTime date =
              DateTime.tryParse(notif['created_at'] ?? '') ?? DateTime.now();
          String formattedDate = DateFormat('MMM d, HH:mm').format(date);

          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: AppSurface(
              padding: const EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      isAlert
                          ? Icons.warning_amber_rounded
                          : Icons.info_outline_rounded,
                      color: color,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          notif['message'] ?? 'Unknown alert',
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 16,
                            height: 1.25,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 10),
                        StatusPill(
                          label: formattedDate,
                          color: color,
                          icon: Icons.schedule_rounded,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    }

    return AppPage(
      title: 'Alerts',
      subtitle: 'Issues that need attention',
      actions: [
        IconButton(
          icon: const Icon(Icons.refresh_rounded),
          onPressed: () {
            setState(() => _isLoading = true);
            _fetchNotifications();
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
