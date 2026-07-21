import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';

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
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error', style: const TextStyle(color: Colors.red)));
    if (_notifications.isEmpty) return const Center(child: Text('No new notifications.', style: TextStyle(color: Colors.white)));

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _notifications.length,
      itemBuilder: (context, index) {
        final notif = _notifications[index];
        final isAlert = notif['type'] == 'ALERT';
        
        DateTime date = DateTime.tryParse(notif['created_at'] ?? '') ?? DateTime.now();
        String formattedDate = DateFormat('MMM d, HH:mm').format(date);

        return Card(
          color: const Color(0xFF1E293B),
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: isAlert ? Colors.redAccent.withValues(alpha: 0.5) : Colors.transparent),
          ),
          child: ListTile(
            leading: Icon(
              isAlert ? Icons.warning_amber_rounded : Icons.info_outline,
              color: isAlert ? Colors.redAccent : Colors.blueAccent,
              size: 32,
            ),
            title: Text(notif['message'] ?? 'Unknown alert', style: const TextStyle(color: Colors.white, fontSize: 16)),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8.0),
              child: Text(formattedDate, style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ),
            isThreeLine: true,
          ),
        );
      },
    );
  }
}
