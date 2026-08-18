import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/remote_data_source.dart';
import 'camera_view.dart';
import 'package:dio/dio.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_theme.dart';

class HomeView extends ConsumerStatefulWidget {
  final bool loadInitialData;

  const HomeView({super.key, this.loadInitialData = true});

  @override
  ConsumerState<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends ConsumerState<HomeView> {
  bool _isLoading = false;
  bool _isConnecting = false;
  bool _isConnected = false;
  String? _errorMessage;
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    if (widget.loadInitialData) {
      _fetchStats();
    }
  }

  void _showSettingsDialog() {
    final controller = TextEditingController(
      text: DioClient().dio.options.baseUrl,
    );
    bool isTesting = false;
    String? testResult;
    bool? testSuccess;

    showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Row(
                children: [
                  Icon(Icons.dns_rounded, color: AppColors.primary),
                  SizedBox(width: 10),
                  Text('Server Configuration'),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Select a preset or enter your backend server URL:',
                      style: TextStyle(color: AppColors.muted, fontSize: 13),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ActionChip(
                          avatar: const Icon(Icons.smartphone_rounded, size: 16),
                          label: const Text('Physical Device (192.168.1.55)'),
                          onPressed: () {
                            setDialogState(() {
                              controller.text = 'http://192.168.1.55:8000/api/v1';
                              testResult = null;
                            });
                          },
                        ),
                        ActionChip(
                          avatar: const Icon(Icons.phone_android, size: 16),
                          label: const Text('Emulator (10.0.2.2)'),
                          onPressed: () {
                            setDialogState(() {
                              controller.text = 'http://10.0.2.2:8000/api/v1';
                              testResult = null;
                            });
                          },
                        ),
                        ActionChip(
                          avatar: const Icon(Icons.laptop, size: 16),
                          label: const Text('Localhost (127.0.0.1)'),
                          onPressed: () {
                            setDialogState(() {
                              controller.text = 'http://127.0.0.1:8000/api/v1';
                              testResult = null;
                            });
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: controller,
                      decoration: const InputDecoration(
                        labelText: 'API Base URL',
                        hintText: 'http://<your-ip>:8000/api/v1',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.link_rounded),
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: isTesting
                          ? null
                          : () async {
                              final url = controller.text.trim();
                              if (url.isEmpty) return;
                              setDialogState(() {
                                isTesting = true;
                                testResult = 'Testing connection...';
                                testSuccess = null;
                              });
                              final ok = await DioClient().testConnection(url);
                              setDialogState(() {
                                isTesting = false;
                                testSuccess = ok;
                                testResult = ok
                                    ? 'Connected successfully!'
                                    : 'Failed to connect. Ensure backend is running.';
                              });
                            },
                      icon: isTesting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.network_check_rounded),
                      label: const Text('Test Connection'),
                    ),
                    if (testResult != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        testResult!,
                        style: TextStyle(
                          color: testSuccess == true
                              ? AppColors.success
                              : AppColors.danger,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final url = controller.text.trim();
                    if (url.isNotEmpty) {
                      await DioClient().updateBaseUrl(url);
                      if (!dialogContext.mounted) return;
                      Navigator.pop(dialogContext);
                      if (mounted) {
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          SnackBar(
                            content: Text('Server URL set to: $url'),
                            backgroundColor: AppColors.success,
                          ),
                        );
                        _fetchStats();
                      }
                    }
                  },
                  child: const Text('Save & Apply'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _fetchStats() async {
    setState(() {
      _isConnecting = true;
      _errorMessage = null;
    });
    try {
      final remoteData = RemoteDataSource();
      final stats = await remoteData.getStats();
      if (mounted) {
        setState(() {
          _stats = stats;
          _isConnected = true;
          _isConnecting = false;
          _errorMessage = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isConnected = false;
          _isConnecting = false;
          _errorMessage =
              'Could not connect to ${DioClient().dio.options.baseUrl}';
        });
      }
    }
  }

  Future<void> _startVerification() async {
    setState(() => _isLoading = true);
    try {
      final remoteData = RemoteDataSource();
      final sessionId = await remoteData.startSession();

      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => CameraView(sessionId: sessionId)),
        ).then((_) {
          _fetchStats(); // Refresh stats when returning
        });
      }
    } on DioException catch (e) {
      if (mounted) {
        String errorMsg = "Network Error: Could not connect to backend.";
        if (e.type == DioExceptionType.connectionTimeout) {
          errorMsg =
              "Connection Timed Out. Please check your server IP in Settings.";
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMsg),
            backgroundColor: Colors.redAccent,
            behavior: SnackBarBehavior.floating,
            action: SnackBarAction(
              label: 'Configure',
              textColor: Colors.white,
              onPressed: _showSettingsDialog,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.redAccent,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildDashboard() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!_isConnected && _errorMessage != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.danger.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.danger.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.cloud_off_rounded, color: AppColors.danger),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Backend Offline / Unreachable',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.danger,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          _errorMessage!,
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 11,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  TextButton(
                    onPressed: _showSettingsDialog,
                    child: const Text('Fix IP'),
                  ),
                ],
              ),
            ),
          ],
          AppSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Active Shift',
                      style: TextStyle(
                        color: AppColors.muted,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    GestureDetector(
                      onTap: _showSettingsDialog,
                      child: StatusPill(
                        label: _isConnecting
                            ? 'CHECKING'
                            : (_isConnected ? 'ONLINE' : 'OFFLINE'),
                        color: _isConnecting
                            ? AppColors.warning
                            : (_isConnected
                                ? AppColors.success
                                : AppColors.danger),
                        icon: _isConnected
                            ? Icons.wifi_rounded
                            : Icons.wifi_off_rounded,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  _stats?["operator_name"] ??
                      (_isConnecting ? "Connecting..." : "Door Staff"),
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _isConnected
                      ? 'Connected to ${DioClient().dio.options.baseUrl}'
                      : 'Tap server icon above to configure backend address.',
                  style: const TextStyle(
                    color: AppColors.muted,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildStatCard(
                'Verified',
                _stats != null ? _stats!["verified"].toString() : '-',
                AppColors.primary,
                Icons.check_circle_outline_rounded,
              ),
              _buildStatCard(
                'Pending',
                _stats != null ? _stats!["pending"].toString() : '-',
                AppColors.warning,
                Icons.hourglass_empty_rounded,
              ),
              _buildStatCard(
                'Flagged',
                _stats != null ? _stats!["flagged"].toString() : '-',
                AppColors.danger,
                Icons.warning_amber_rounded,
              ),
            ],
          ),
          const Spacer(),
          ElevatedButton(
            onPressed: _isLoading ? null : _startVerification,
            child: _isLoading
                ? const SizedBox(
                    height: 24,
                    width: 24,
                    child: CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 3,
                    ),
                  )
                : const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.document_scanner_rounded),
                      SizedBox(width: 10),
                      Text('Start Verification'),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(
    String label,
    String value,
    Color color,
    IconData icon,
  ) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 8),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppColors.line),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 12),
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 26,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      title: 'Security Portal',
      subtitle: 'Door team verification',
      actions: [
        IconButton(
          tooltip: 'Configure Backend Server IP',
          icon: const Icon(Icons.settings_outlined),
          onPressed: _showSettingsDialog,
        ),
        IconButton(
          tooltip: 'Refresh Status',
          icon: const Icon(Icons.sync_rounded),
          onPressed: _fetchStats,
        ),
      ],
      child: _buildDashboard(),
    );
  }
}
