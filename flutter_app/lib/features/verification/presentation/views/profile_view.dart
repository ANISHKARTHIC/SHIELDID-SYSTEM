import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/security/token_storage.dart';
import '../../../../core/security/biometric_auth_service.dart';
import '../../../../core/security/biometric_prefs.dart';
import '../../../../core/providers/theme_mode_provider.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/app_snackbar.dart';
import '../../../../core/navigation/app_page_route.dart';
import '../../data/datasources/remote_data_source.dart';
import 'connection_settings_view.dart';

class ProfileView extends ConsumerStatefulWidget {
  final VoidCallback onLoggedOut;

  const ProfileView({super.key, required this.onLoggedOut});

  @override
  ConsumerState<ProfileView> createState() => _ProfileViewState();
}

class _ProfileViewState extends ConsumerState<ProfileView> {
  String? _email;
  String? _role;
  bool _biometricEnabled = false;
  bool _biometricAvailable = false;
  bool _checkingBiometric = true;

  bool _isCheckingUpdate = true;
  String? _currentVersion;
  String? _latestVersion;
  String? _updateUrl;
  bool? _updateAvailable;

  @override
  void initState() {
    super.initState();
    _loadProfile();
    _loadBiometricState();
    // Checked immediately on opening Profile — this is the first thing
    // staff should see here, not something reachable only by drilling
    // into Connection settings.
    _checkForUpdate();
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
    setState(() => _isCheckingUpdate = true);
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
      setState(() => _updateAvailable = null);
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
        showAppErrorSnackBar(context, 'Could not open update link');
      }
    }
  }

  Future<void> _loadProfile() async {
    final email = await TokenStorage.readEmail();
    final role = await TokenStorage.readRole();
    if (mounted) {
      setState(() {
        _email = email;
        _role = role;
      });
    }
  }

  Future<void> _loadBiometricState() async {
    final available = await BiometricAuthService.isAvailable();
    final enabled = await BiometricPrefs.isEnabled();
    if (mounted) {
      setState(() {
        _biometricAvailable = available;
        _biometricEnabled = enabled && available;
        _checkingBiometric = false;
      });
    }
  }

  Future<void> _toggleBiometric(bool value) async {
    HapticFeedback.selectionClick();
    if (value) {
      final success = await BiometricAuthService.authenticate(
        reason: 'Confirm biometric unlock for VenuePass',
      );
      if (!success) {
        if (mounted) {
          showAppErrorSnackBar(
            context,
            'Could not verify biometrics. Not enabled.',
          );
        }
        return;
      }
    }
    await BiometricPrefs.setEnabled(value);
    if (mounted) setState(() => _biometricEnabled = value);
  }

  Future<void> _confirmLogout() async {
    HapticFeedback.selectionClick();
    final confirmed = await showAppConfirmDialog(
      context,
      title: 'Sign out?',
      message: 'You will need to sign in again to verify customers.',
      confirmLabel: 'Sign Out',
      isDestructive: true,
      icon: Icons.logout_rounded,
    );

    if (confirmed == true) {
      await TokenStorage.clear();
      widget.onLoggedOut();
    }
  }

  String _formatRole(String? role) {
    if (role == null) return '';
    return role
        .split('_')
        .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final themeMode = ref.watch(themeModeProvider);

    return AppPage(
      title: 'Profile',
      child: ListView(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
        children: [
          _buildUpdateCard(colors),
          const SizedBox(height: 22),
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: colors.primarySoft,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(Icons.person_rounded, color: colors.ink, size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _email ?? '—',
                      style: AppTypography.headline.copyWith(color: colors.ink),
                    ),
                    const SizedBox(height: 4),
                    StatusPill(label: _formatRole(_role), color: colors.muted),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          Divider(color: colors.line, height: 1),
          const SizedBox(height: 22),
          Text(
            'CONNECTION',
            style: AppTypography.caption.copyWith(
              color: colors.muted,
              letterSpacing: 0.06,
            ),
          ),
          const SizedBox(height: 6),
          InkWell(
            onTap: () {
              HapticFeedback.selectionClick();
              Navigator.of(
                context,
              ).push(AppPageRoute.push(const ConnectionSettingsView()));
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Row(
                children: [
                  Icon(Icons.dns_rounded, size: 18, color: colors.ink),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Server & Service Status',
                          style: AppTypography.callout.copyWith(
                            fontWeight: FontWeight.w600,
                            color: colors.ink,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Configure the backend address and check connectivity',
                          style: AppTypography.footnote.copyWith(
                            color: colors.muted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded, color: colors.muted, size: 20),
                ],
              ),
            ),
          ),
          const SizedBox(height: 22),
          Divider(color: colors.line, height: 1),
          const SizedBox(height: 22),
          Text(
            'PREFERENCES',
            style: AppTypography.caption.copyWith(
              color: colors.muted,
              letterSpacing: 0.06,
            ),
          ),
          const SizedBox(height: 6),
          _buildPrefRow(
            colors,
            icon: Icons.dark_mode_rounded,
            title: 'Dark Mode',
            value: themeMode == ThemeMode.dark,
            onChanged: (value) {
              HapticFeedback.selectionClick();
              ref
                  .read(themeModeProvider.notifier)
                  .setMode(value ? ThemeMode.dark : ThemeMode.light);
            },
          ),
          Divider(color: colors.line, height: 1),
          _buildPrefRow(
            colors,
            icon: Icons.fingerprint_rounded,
            title: 'Face ID Unlock',
            subtitle: _checkingBiometric
                ? null
                : (_biometricAvailable
                      ? 'Adds a device-local check'
                      : 'Unavailable on this device'),
            value: _biometricEnabled,
            onChanged: _biometricAvailable ? _toggleBiometric : null,
          ),
          const SizedBox(height: 22),
          Divider(color: colors.line, height: 1),
          InkWell(
            onTap: _confirmLogout,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Row(
                children: [
                  Icon(Icons.logout_rounded, color: colors.danger, size: 18),
                  const SizedBox(width: 12),
                  Text(
                    'Sign Out',
                    style: AppTypography.callout.copyWith(
                      fontWeight: FontWeight.w700,
                      color: colors.danger,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// First thing shown on Profile — checked automatically on open, not
  /// tucked one tap deeper inside Connection settings. Tapping it always
  /// opens Connection settings (for the full version/status detail and,
  /// when relevant, the "Update Now" download); this card itself is a
  /// summary, not the update button's only home.
  Widget _buildUpdateCard(AppColorsExt colors) {
    final hasUpdate = _updateAvailable == true;
    final bg = hasUpdate ? colors.warningSoft : colors.surface;
    final accent = hasUpdate ? colors.warning : colors.primary;

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () {
        HapticFeedback.selectionClick();
        Navigator.of(
          context,
        ).push(AppPageRoute.push(const ConnectionSettingsView()));
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: hasUpdate ? accent.withValues(alpha: 0.5) : colors.line,
            width: hasUpdate ? 1.5 : 1,
          ),
        ),
        child: Row(
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
                size: 22,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _isCheckingUpdate
                        ? 'Checking for updates…'
                        : hasUpdate
                            ? 'Update available: v$_latestVersion'
                            : _updateAvailable == null
                                ? 'Could not check for updates'
                                : 'App is up to date',
                    style: TextStyle(
                      color: colors.ink,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (_currentVersion != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Current version: $_currentVersion',
                      style: TextStyle(
                        color: colors.muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (_isCheckingUpdate)
              SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2.2, color: accent),
              )
            else if (hasUpdate)
              SizedBox(
                height: 36,
                child: ElevatedButton(
                  onPressed: _openUpdateUrl,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: accent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
                    // The app theme's default ElevatedButton style forces
                    // minimumSize to Size.fromHeight(56), i.e. infinite
                    // width, for the full-width primary-action buttons
                    // used everywhere else. Left unset here, this compact
                    // inline button inherited that and demanded infinite
                    // width inside this Row, squeezing the Expanded text
                    // next to it down to near-zero — which is what made
                    // "Update available: v1.0.3" render one character per
                    // line. minimumSize: Size.zero opts this one button
                    // back out, sized to its own content instead.
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Update'),
                ),
              )
            else
              Icon(Icons.chevron_right_rounded, color: colors.muted, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildPrefRow(
    AppColorsExt colors, {
    required IconData icon,
    required String title,
    String? subtitle,
    required bool value,
    required ValueChanged<bool>? onChanged,
  }) {
    final enabled = onChanged != null;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: Row(
        children: [
          Icon(icon, size: 18, color: enabled ? colors.ink : colors.muted),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.callout.copyWith(
                    fontWeight: FontWeight.w600,
                    color: enabled ? colors.ink : colors.muted,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: AppTypography.footnote.copyWith(
                      color: colors.muted,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ),
          Switch(value: value, onChanged: onChanged),
        ],
      ),
    );
  }
}
