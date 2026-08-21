import 'package:flutter/material.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_snackbar.dart';

/// Server address configuration and live backend/AI-service connection
/// status. Moved off the dashboard (home_view.dart) — the operator's main
/// screen should show operational info (occupancy, stats, recent
/// activity), not infrastructure status; this technical detail belongs
/// here on the Profile tab where it's reachable but out of the way.
class ConnectionSettingsView extends StatefulWidget {
  const ConnectionSettingsView({super.key});

  @override
  State<ConnectionSettingsView> createState() => _ConnectionSettingsViewState();
}

class _ConnectionSettingsViewState extends State<ConnectionSettingsView> {
  late final TextEditingController _urlController;
  bool _isTesting = false;
  String? _testResult;
  bool? _testSuccess;

  bool _isLoadingReadiness = true;
  Map<String, dynamic>? _readiness;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: DioClient().dio.options.baseUrl);
    _fetchReadiness();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _fetchReadiness() async {
    setState(() => _isLoadingReadiness = true);
    try {
      final readiness = await RemoteDataSource().getReadiness();
      if (mounted) setState(() => _readiness = readiness);
    } catch (e) {
      if (mounted) setState(() => _readiness = null);
    } finally {
      if (mounted) setState(() => _isLoadingReadiness = false);
    }
  }

  Future<void> _testConnection() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;
    setState(() {
      _isTesting = true;
      _testResult = 'Testing connection...';
      _testSuccess = null;
    });
    final ok = await DioClient().testConnection(url);
    if (!mounted) return;
    setState(() {
      _isTesting = false;
      _testSuccess = ok;
      _testResult = ok
          ? 'Connected successfully!'
          : 'Failed to connect. Ensure the server is running.';
    });
  }

  Future<void> _saveAndApply() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;
    await DioClient().updateBaseUrl(url);
    if (!mounted) return;
    showAppSuccessSnackBar(context, 'Server address updated');
    _fetchReadiness();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final aiReady = _readiness?['checks']?['ai_service'] == 'ok';
    final dbReady = _readiness?['checks']?['database'] == 'ok';

    return AppPage(
      title: 'Connection',
      subtitle: 'Server address and service status',
      child: ListView(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
        children: [
          Text(
            'SERVER ADDRESS',
            style: AppTypography.caption.copyWith(
              color: colors.muted,
              letterSpacing: 0.06,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'API Base URL',
              hintText: 'https://venuepass-api.duckdns.org/api/v1',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.link_rounded),
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _isTesting ? null : _testConnection,
            icon: _isTesting
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.network_check_rounded),
            label: const Text('Test Connection'),
          ),
          if (_testResult != null) ...[
            const SizedBox(height: 8),
            Text(
              _testResult!,
              style: TextStyle(
                color: _testSuccess == true ? colors.success : colors.danger,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _saveAndApply,
            child: const Text('Save & Apply'),
          ),
          const SizedBox(height: 28),
          Divider(color: colors.line, height: 1),
          const SizedBox(height: 22),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'SERVICE STATUS',
                style: AppTypography.caption.copyWith(
                  color: colors.muted,
                  letterSpacing: 0.06,
                ),
              ),
              IconButton(
                tooltip: 'Refresh',
                icon: const Icon(Icons.sync_rounded, size: 18),
                onPressed: _isLoadingReadiness ? null : _fetchReadiness,
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
          const SizedBox(height: 6),
          AppSurface(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Column(
              children: [
                _buildStatusRow(
                  colors,
                  Icons.dns_rounded,
                  'Backend',
                  _isLoadingReadiness
                      ? 'Checking…'
                      : (dbReady ? 'Connected' : 'Unreachable'),
                  _isLoadingReadiness
                      ? colors.muted
                      : (dbReady ? colors.success : colors.danger),
                ),
                Divider(color: colors.line, height: 1),
                _buildStatusRow(
                  colors,
                  Icons.memory_rounded,
                  'AI Service',
                  _isLoadingReadiness
                      ? 'Checking…'
                      : (aiReady ? 'Ready' : 'Unavailable'),
                  _isLoadingReadiness
                      ? colors.muted
                      : (aiReady ? colors.success : colors.danger),
                ),
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
              Text(
                label,
                style: TextStyle(
                  color: colors.muted,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          Text(
            value,
            style: TextStyle(
              color: valueColor,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
