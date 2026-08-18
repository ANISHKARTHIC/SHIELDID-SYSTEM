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
        reason: 'Confirm biometric unlock for Pub Entry Staff',
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
        padding: const EdgeInsets.all(18),
        children: [
          AppSurface(
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: colors.primarySoft,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(
                    Icons.person_rounded,
                    color: colors.primary,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _email ?? '—',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: colors.ink,
                        ),
                      ),
                      const SizedBox(height: 4),
                      StatusPill(
                        label: _formatRole(_role),
                        color: colors.primary,
                        icon: Icons.shield_outlined,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Text(
            'PREFERENCES',
            style: TextStyle(color: colors.muted, fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 0.6),
          ),
          const SizedBox(height: 10),
          AppSurface(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                SwitchListTile(
                  secondary: Icon(Icons.dark_mode_rounded, color: colors.ink),
                  title: Text('Dark Mode', style: TextStyle(fontWeight: FontWeight.w700, color: colors.ink)),
                  value: themeMode == ThemeMode.dark,
                  onChanged: (value) {
                    ref.read(themeModeProvider.notifier).setMode(
                          value ? ThemeMode.dark : ThemeMode.light,
                        );
                  },
                ),
                Divider(height: 1, color: colors.line),
                SwitchListTile(
                  secondary: Icon(
                    Icons.fingerprint_rounded,
                    color: _biometricAvailable ? colors.ink : colors.muted,
                  ),
                  title: Text(
                    'Require Face ID / Fingerprint to unlock',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: _biometricAvailable ? colors.ink : colors.muted,
                    ),
                  ),
                  subtitle: _checkingBiometric
                      ? null
                      : Text(
                          _biometricAvailable
                              ? 'Adds a device-local unlock check on top of your account.'
                              : 'Biometric unlock unavailable on this device.',
                          style: TextStyle(color: colors.muted, fontSize: 12),
                        ),
                  value: _biometricEnabled,
                  onChanged: _biometricAvailable ? _toggleBiometric : null,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          AppSurface(
            padding: EdgeInsets.zero,
            child: ListTile(
              leading: Icon(Icons.logout_rounded, color: colors.danger),
              title: Text(
                'Sign Out',
                style: TextStyle(fontWeight: FontWeight.w700, color: colors.danger),
              ),
              onTap: _confirmLogout,
            ),
          ),
        ],
      ),
    );
  }
}
