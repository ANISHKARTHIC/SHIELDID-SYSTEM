import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/security/token_storage.dart';
import '../../../../core/security/biometric_auth_service.dart';
import '../../../../core/security/biometric_prefs.dart';
import '../../../../core/providers/theme_mode_provider.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/app_snackbar.dart';

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

  @override
  void initState() {
    super.initState();
    _loadProfile();
    _loadBiometricState();
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
    if (value) {
      final success = await BiometricAuthService.authenticate(
        reason: 'Confirm biometric unlock for VenuePass',
      );
      if (!success) {
        if (mounted) showAppErrorSnackBar(context, 'Could not verify biometrics. Not enabled.');
        return;
      }
    }
    await BiometricPrefs.setEnabled(value);
    if (mounted) setState(() => _biometricEnabled = value);
  }

  Future<void> _confirmLogout() async {
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
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: colors.ink),
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
            'PREFERENCES',
            style: TextStyle(color: colors.muted, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.06),
          ),
          const SizedBox(height: 6),
          _buildPrefRow(
            colors,
            icon: Icons.dark_mode_rounded,
            title: 'Dark Mode',
            value: themeMode == ThemeMode.dark,
            onChanged: (value) {
              ref.read(themeModeProvider.notifier).setMode(
                    value ? ThemeMode.dark : ThemeMode.light,
                  );
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
                    style: TextStyle(fontWeight: FontWeight.w700, color: colors.danger, fontSize: 14),
                  ),
                ],
              ),
            ),
          ),
        ],
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
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: enabled ? colors.ink : colors.muted,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(subtitle, style: TextStyle(color: colors.muted, fontSize: 12)),
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
