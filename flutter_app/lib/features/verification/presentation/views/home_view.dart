import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/remote_data_source.dart';
import 'camera_view.dart';
import 'package:dio/dio.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/navigation/app_page_route.dart';
import '../../../../core/widgets/app_snackbar.dart';

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
  Map<String, dynamic>? _readiness;

  @override
  void initState() {
    super.initState();
    if (widget.loadInitialData) {
      _fetchStats();
      _fetchReadiness();
    }
  }

  Future<void> _fetchReadiness() async {
    try {
      final remoteData = RemoteDataSource();
      final readiness = await remoteData.getReadiness();
      if (mounted) setState(() => _readiness = readiness);
    } catch (e) {
      if (mounted) setState(() => _readiness = null);
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
            final colors = context.colors;
            return AlertDialog(
              backgroundColor: colors.surface,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: Row(
                children: [
                  Icon(Icons.dns_rounded, color: colors.primary),
                  const SizedBox(width: 10),
                  const Text('Server Configuration'),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Enter the backend server address for this venue:',
                      style: TextStyle(color: colors.muted, fontSize: 13),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: controller,
                      decoration: const InputDecoration(
                        labelText: 'API Base URL',
                        hintText: 'http://<server-address>:8000/api/v1',
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
                          color: testSuccess == true ? colors.success : colors.danger,
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
                        showAppSuccessSnackBar(this.context, 'Server address updated');
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
          _errorMessage = 'Unable to reach the verification service.';
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
        Navigator.of(context)
            .push(AppPageRoute.push(CameraView(sessionId: sessionId)))
            .then((_) {
          _fetchStats(); // Refresh stats when returning
          _fetchReadiness();
        });
      }
    } on DioException catch (e) {
      if (mounted) {
        String errorMsg = "Could not connect to the verification service.";
        if (e.type == DioExceptionType.connectionTimeout) {
          errorMsg = "Connection timed out. Check the server configuration.";
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMsg),
            backgroundColor: context.colors.dangerSoft,
            behavior: SnackBarBehavior.floating,
            action: SnackBarAction(
              label: 'Configure',
              textColor: context.colors.primary,
              onPressed: _showSettingsDialog,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        showAppErrorSnackBar(context, 'Something went wrong. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildDashboard() {
    final colors = context.colors;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (!_isConnected && _errorMessage != null) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colors.danger.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: colors.danger.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.cloud_off_rounded, color: colors.danger),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Backend Offline / Unreachable',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: colors.danger,
                            fontSize: 13,
                          ),
                        ),
                        Text(
                          _errorMessage!,
                          style: TextStyle(color: colors.muted, fontSize: 11),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  TextButton(
                    onPressed: _showSettingsDialog,
                    child: const Text('Fix'),
                  ),
                ],
              ),
            ),
          ],
          GestureDetector(
            onLongPress: _showSettingsDialog,
            child: AppSurface(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'ACTIVE SHIFT',
                        style: TextStyle(
                          color: colors.muted,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.06,
                        ),
                      ),
                      StatusPill(
                        label: _isConnecting
                            ? 'CHECKING'
                            : (_isConnected ? 'ONLINE' : 'OFFLINE'),
                        color: _isConnecting
                            ? colors.warning
                            : (_isConnected ? colors.success : colors.danger),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _stats?["operator_name"] ??
                        (_isConnecting ? "Connecting..." : "Door Staff"),
                    style: TextStyle(
                      color: colors.ink,
                      fontSize: 26,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.01,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _isConnected
                        ? 'Connected to verification service.'
                        : 'Not connected. Long-press to configure.',
                    style: TextStyle(
                      color: colors.muted,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          AppSurface(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 20),
            child: Row(
              children: [
                _buildStatColumn(colors, 'Verified', _stats != null ? _stats!["verified"].toString() : '-', colors.ink, isFirst: true),
                _buildStatColumn(colors, 'Pending', _stats != null ? _stats!["pending"].toString() : '-', colors.ink),
                _buildStatColumn(colors, 'Flagged', _stats != null ? _stats!["flagged"].toString() : '-', colors.warning, isLast: true),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppSurface(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Column(
              children: [
                _buildStatusRow(
                  colors,
                  Icons.wifi_rounded,
                  'Network',
                  _isConnected ? 'Connected' : 'Offline',
                  _isConnected ? colors.success : colors.danger,
                ),
                Divider(color: colors.line, height: 1),
                _buildStatusRow(
                  colors,
                  Icons.memory_rounded,
                  'AI Service',
                  _readiness?['checks']?['ai_service'] == 'ok' ? 'Ready' : 'Unavailable',
                  _readiness?['checks']?['ai_service'] == 'ok' ? colors.success : colors.muted,
                ),
                Divider(color: colors.line, height: 1),
                _buildStatusRow(
                  colors,
                  Icons.sync_rounded,
                  'Sync',
                  _isConnected ? 'Up to date' : 'Pending',
                  colors.ink,
                ),
              ],
            ),
          ),
          const SizedBox(height: 28),
          ElevatedButton(
            onPressed: _isLoading ? null : _startVerification,
            child: _isLoading
                ? SizedBox(
                    height: 24,
                    width: 24,
                    child: CircularProgressIndicator(
                      color: colors.onPrimary,
                      strokeWidth: 3,
                    ),
                  )
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.document_scanner_rounded, color: colors.onPrimary),
                      const SizedBox(width: 10),
                      Text('Start Verification', style: TextStyle(color: colors.onPrimary)),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusRow(
    AppColorsExt colors,
    IconData icon,
    String label,
    String value,
    Color valueColor,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(icon, size: 15, color: colors.muted),
              const SizedBox(width: 8),
              Text(label, style: TextStyle(color: colors.muted, fontSize: 13, fontWeight: FontWeight.w500)),
            ],
          ),
          Text(value, style: TextStyle(color: valueColor, fontSize: 13, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _buildStatColumn(
    AppColorsExt colors,
    String label,
    String value,
    Color valueColor, {
    bool isFirst = false,
    bool isLast = false,
  }) {
    return Expanded(
      child: Container(
        padding: EdgeInsets.only(
          right: isLast ? 0 : 16,
          left: isFirst ? 0 : 16,
        ),
        decoration: BoxDecoration(
          border: Border(
            right: isLast ? BorderSide.none : BorderSide(color: colors.line),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              value,
              style: TextStyle(
                color: valueColor,
                fontSize: 26,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.01,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: colors.muted,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.02,
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
          tooltip: 'Refresh Status',
          icon: const Icon(Icons.sync_rounded),
          onPressed: () {
            _fetchStats();
            _fetchReadiness();
          },
        ),
      ],
      child: _buildDashboard(),
    );
  }
}
