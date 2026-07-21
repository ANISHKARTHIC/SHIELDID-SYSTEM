import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import 'package:intl/intl.dart';

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
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error', style: const TextStyle(color: Colors.red)));
    if (_history.isEmpty) return const Center(child: Text('No verification history found.', style: TextStyle(color: Colors.white)));

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _history.length,
      itemBuilder: (context, index) {
        final item = _history[index];
        final isPass = item['final_decision'] == 'pass';
        
        DateTime date = DateTime.tryParse(item['created_at'] ?? '') ?? DateTime.now();
        String formattedDate = DateFormat('MMM d, yyyy - HH:mm').format(date);

        return Card(
          color: const Color(0xFF1E293B),
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: isPass ? Colors.green.withValues(alpha: 0.2) : Colors.red.withValues(alpha: 0.2),
              child: Icon(isPass ? Icons.check : Icons.warning, color: isPass ? Colors.green : Colors.red),
            ),
            title: Text('Session ${item['session_id'].toString().substring(0, 8)}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            subtitle: Text(formattedDate, style: const TextStyle(color: Colors.grey)),
            trailing: Text(
              (item['final_decision'] ?? 'PENDING').toString().toUpperCase(),
              style: TextStyle(
                color: isPass ? Colors.green : Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        );
      },
    );
  }
}
