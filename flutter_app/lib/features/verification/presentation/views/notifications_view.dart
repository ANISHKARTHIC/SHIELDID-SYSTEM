import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/empty_state.dart';
import '../../../../core/widgets/branded_loading.dart';

class NotificationsView extends StatefulWidget {
  const NotificationsView({super.key});

  @override
  State<NotificationsView> createState() => _NotificationsViewState();
}

class _NotificationsViewState extends State<NotificationsView> {
  bool _isLoading = true;
  bool _isFirstLoad = true;
  List<dynamic> _notifications = [];
  String? _error;
  Timer? _pollTimer;
  int? _lastAlertCount;

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
    // 10s: an in-venue ban alert is time-sensitive enough to poll faster
    // than routine list views, but 3s was excessive load for a t3.micro
    // backend — matches the admin console's own notifications interval.
    _pollTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _fetchNotifications(),
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchNotifications() async {
    try {
      final remoteData = RemoteDataSource();
      final notifications = await remoteData.getNotifications();
      final alertCount = notifications
          .where((n) => n['type'] == 'ALERT')
          .length;
      // A new ALERT arriving mid-poll (not the first load) is exactly the
      // moment door staff need a tactile nudge — an in-venue ban escort
      // alert shouldn't rely on someone visually re-checking the tab.
      if (!_isFirstLoad &&
          _lastAlertCount != null &&
          alertCount > _lastAlertCount!) {
        HapticFeedback.heavyImpact();
      }
      _lastAlertCount = alertCount;
      if (mounted) {
        setState(() {
          _notifications = notifications;
          _isLoading = false;
          _isFirstLoad = false;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
          _isFirstLoad = false;
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
        const BrandedLoadingIndicator(icon: Icons.notifications_none_rounded),
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
        separatorBuilder: (context, index) =>
            Divider(color: colors.line, height: 1),
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
                        style: AppTypography.body.copyWith(
                          color: colors.ink,
                          height: 1.3,
                          fontWeight: isUnread
                              ? FontWeight.w700
                              : FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        formattedDate,
                        style: AppTypography.footnote.copyWith(
                          color: colors.muted,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                if (isUnread)
                  Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.only(top: 5),
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
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
            HapticFeedback.selectionClick();
            setState(() => _isLoading = true);
            _fetchNotifications();
          },
        ),
      ],
      child: RefreshIndicator(onRefresh: _fetchNotifications, child: content),
    );
  }
}
