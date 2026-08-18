import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/empty_state.dart';

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
          title: 'Alerts unavailable',
          message: _error!,
          color: colors.danger,
        ),
      );
    } else if (_notifications.isEmpty) {
      content = _scrollableEmptyState(
        EmptyState(
          icon: Icons.notifications_none_rounded,
          title: 'No new alerts',
          message: 'Flagged sessions and supervisor messages will appear here.',
          color: colors.primary,
        ),
      );
    } else {
      content = ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
        itemCount: _notifications.length,
        separatorBuilder: (context, index) => Divider(color: colors.line, height: 1),
        itemBuilder: (context, index) {
          final notif = _notifications[index];
          final isAlert = notif['type'] == 'ALERT';
          final isUnread = notif['is_read'] == false;
          final color = isAlert ? colors.danger : colors.ink;

          DateTime date =
              DateTime.tryParse(notif['created_at'] ?? '') ?? DateTime.now();
          String formattedDate = DateFormat('MMM d, HH:mm').format(date);

          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    isAlert
                        ? Icons.warning_amber_rounded
                        : Icons.info_outline_rounded,
                    color: color,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        (notif['message'] as String?)?.trim().isNotEmpty == true
                            ? notif['message']
                            : 'Alert',
                        style: TextStyle(
                          color: colors.ink,
                          fontSize: 15,
                          height: 1.3,
                          fontWeight: isUnread ? FontWeight.w700 : FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        formattedDate,
                        style: TextStyle(color: colors.muted, fontSize: 12, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
                if (isUnread)
                  Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.only(top: 5),
                    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                  ),
              ],
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
      child: RefreshIndicator(
        onRefresh: _fetchNotifications,
        child: content,
      ),
    );
  }
}
