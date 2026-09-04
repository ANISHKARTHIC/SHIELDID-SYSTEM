import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_snackbar.dart';

/// Server address (fixed — not user-editable, avoids per-device/per-venue
/// IP misconfiguration) and live backend/AI-service connection status,
/// plus an app-version update check. Moved off the dashboard
/// (home_view.dart) — the operator's main screen should show operational
/// info (occupancy, stats, recent activity), not infrastructure status;
/// this technical detail belongs here on the Profile tab where it's
/// reachable but out of the way.
class ConnectionSettingsView extends StatefulWidget {
  const ConnectionSettingsView({super.key});

  @override
  State<ConnectionSettingsView> createState() => _ConnectionSettingsViewState();
}

class _ConnectionSettingsViewState extends State<ConnectionSettingsView> {
  bool _isLoadingReadiness = true;
  Map<String, dynamic>? _readiness;

  bool _isCheckingUpdate = false;
  String? _currentVersion;
  String? _latestVersion;
  String? _updateUrl;
  bool? _updateAvailable;
  String? _updateCheckError;

  @override
  void initState() {
    super.initState();
    _fetchReadiness();
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

  int _compareVersions(String a, String b) {
    final partsA = a.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    final partsB = b.split('.').map((p) => int.tryParse(p) ?? 0).toList();
    final length = partsA.length > partsB.length ? partsA.length : partsB.length;
    for (var i = 0; i < length; i++) {
      final va = i < partsA.length ? partsA[i] : 0;
      final vb = i < partsB.length ? partsB[i] : 0;
      if (va != vb) return va.compareTo(vb);
    }
    return 0;
  }

  Future<void> _checkForUpdate() async {
    setState(() {
      _isCheckingUpdate = true;
      _updateCheckError = null;
      _updateAvailable = null;
    });
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      final latest = await RemoteDataSource().getLatestVersion();
      final latestVersion = (latest['latest_version'] ?? '').toString();
      if (!mounted) return;
      setState(() {
        _currentVersion = packageInfo.version;
        _latestVersion = latestVersion.isNotEmpty ? latestVersion : null;
        _updateUrl = (latest['update_url'] ?? '').toString();
        _updateAvailable = _latestVersion != null &&
            _compareVersions(_latestVersion!, packageInfo.version) > 0;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _updateCheckError = 'Could not check for updates. Ensure the server is reachable.';
      });
    } finally {
      if (mounted) setState(() => _isCheckingUpdate = false);
    }
  }

  Future<void> _openUpdateUrl() async {
    final url = _updateUrl;
    if (url == null || url.isEmpty) return;
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (mounted) {
        showAppSuccessSnackBar(context, 'Could not open update link');
      }
    }
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
          AppSurface(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                Icon(Icons.link_rounded, size: 18, color: colors.muted),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    DioClient().dio.options.baseUrl,
                    style: TextStyle(
                      color: colors.ink,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
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
          const SizedBox(height: 28),
          Divider(color: colors.line, height: 1),
          const SizedBox(height: 22),
          Text(
            'APP VERSION',
            style: AppTypography.caption.copyWith(
              color: colors.muted,
              letterSpacing: 0.06,
            ),
          ),
          const SizedBox(height: 10),
          AppSurface(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_currentVersion != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      _updateAvailable == true
                          ? 'Update available: $_latestVersion (current $_currentVersion)'
                          : 'Up to date — version $_currentVersion',
                      style: TextStyle(
                        color: _updateAvailable == true ? colors.warning : colors.muted,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                if (_updateCheckError != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      _updateCheckError!,
                      style: TextStyle(
                        color: colors.danger,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isCheckingUpdate ? null : _checkForUpdate,
                        icon: _isCheckingUpdate
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.system_update_rounded),
                        label: const Text('Check for Update'),
                      ),
                    ),
                  ],
                ),
                if (_updateAvailable == true && (_updateUrl ?? '').isNotEmpty) ...[
                  const SizedBox(height: 10),
                  ElevatedButton.icon(
                    onPressed: _openUpdateUrl,
                    icon: const Icon(Icons.download_rounded),
                    label: const Text('Update'),
                  ),
                ],
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
