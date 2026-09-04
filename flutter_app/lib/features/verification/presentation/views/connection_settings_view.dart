import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_snackbar.dart';

/// App-version update check (the primary action on this screen — checked
/// automatically on open and shown as a large hero card up top), server
/// address (fixed — not user-editable, avoids per-device/per-venue IP
/// misconfiguration) and live backend/AI-service connection status. Moved
/// off the dashboard (home_view.dart) — the operator's main screen should
/// show operational info (occupancy, stats, recent activity), not
/// infrastructure status; this technical detail belongs here on the
/// Profile tab where it's reachable but out of the way.
class ConnectionSettingsView extends StatefulWidget {
  const ConnectionSettingsView({super.key});

  @override
  State<ConnectionSettingsView> createState() => _ConnectionSettingsViewState();
}

class _ConnectionSettingsViewState extends State<ConnectionSettingsView> {
  bool _isLoadingReadiness = true;
  Map<String, dynamic>? _readiness;

  bool _isCheckingUpdate = true;
  String? _currentVersion;
  String? _latestVersion;
  String? _updateUrl;
  String? _releaseNotes;
  bool? _updateAvailable;
  String? _updateCheckError;

  @override
  void initState() {
    super.initState();
    _fetchReadiness();
    // Checked immediately on open (not just on button tap) — the update
    // card is the primary reason staff land on this screen, so it
    // shouldn't require an extra tap just to see whether it applies.
    _checkForUpdate();
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
        _releaseNotes = (latest['release_notes'] ?? '').toString();
        _updateAvailable = _latestVersion != null &&
            _compareVersions(_latestVersion!, packageInfo.version) > 0;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _updateAvailable = null;
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
      subtitle: 'App updates, server address and service status',
      child: ListView(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
        children: [
          _buildUpdateHero(colors),
          const SizedBox(height: 28),
          Divider(color: colors.line, height: 1),
          const SizedBox(height: 22),
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
        ],
      ),
    );
  }

  /// The primary action on this screen: a large, first-position card.
  /// Three states — checking, update available (prominent full-width
  /// "Update" button + version/size/notes), or up to date.
  Widget _buildUpdateHero(AppColorsExt colors) {
    final hasUpdate = _updateAvailable == true;
    final bg = hasUpdate ? colors.warningSoft : colors.surface;
    final accent = hasUpdate ? colors.warning : colors.primary;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: hasUpdate ? accent.withValues(alpha: 0.5) : colors.line,
          width: hasUpdate ? 1.5 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  hasUpdate ? Icons.system_update_rounded : Icons.check_circle_rounded,
                  color: accent,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'APP UPDATE',
                      style: AppTypography.caption.copyWith(
                        color: colors.muted,
                        letterSpacing: 0.06,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _isCheckingUpdate
                          ? 'Checking for updates…'
                          : hasUpdate
                              ? 'Update available: v$_latestVersion'
                              : _updateCheckError != null
                                  ? 'Could not check'
                                  : 'You\'re up to date',
                      style: TextStyle(
                        color: colors.ink,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              if (_isCheckingUpdate)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2.4),
                ),
            ],
          ),
          if (_currentVersion != null) ...[
            const SizedBox(height: 10),
            Text(
              'Current version: $_currentVersion',
              style: TextStyle(
                color: colors.muted,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          if (hasUpdate && (_releaseNotes ?? '').isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              _releaseNotes!,
              style: TextStyle(
                color: colors.ink.withValues(alpha: 0.8),
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          if (_updateCheckError != null) ...[
            const SizedBox(height: 8),
            Text(
              _updateCheckError!,
              style: TextStyle(
                color: colors.danger,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          const SizedBox(height: 18),
          if (hasUpdate)
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                onPressed: _openUpdateUrl,
                style: ElevatedButton.styleFrom(
                  backgroundColor: accent,
                  foregroundColor: Colors.white,
                  textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                ),
                icon: const Icon(Icons.download_rounded, size: 22),
                label: const Text('Update Now'),
              ),
            )
          else
            SizedBox(
              width: double.infinity,
              height: 46,
              child: OutlinedButton.icon(
                onPressed: _isCheckingUpdate ? null : _checkForUpdate,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Check Again'),
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
