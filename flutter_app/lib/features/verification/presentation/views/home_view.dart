import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../data/datasources/remote_data_source.dart';
import 'camera_view.dart';
import 'occupancy_view.dart';
import 'package:dio/dio.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/navigation/app_page_route.dart';
import '../../../../core/widgets/app_snackbar.dart';

class HomeView extends ConsumerStatefulWidget {
  final bool loadInitialData;

  /// Switches the bottom nav to the Profile tab, where server/AI-service
  /// connection status and configuration now live — the dashboard itself
  /// no longer shows or manages that technical state (see profile_view.dart's
  /// Connection section).
  final VoidCallback? onOpenSettings;

  const HomeView({super.key, this.loadInitialData = true, this.onOpenSettings});

  @override
  ConsumerState<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends ConsumerState<HomeView> {
  bool _isLoading = false;
  Map<String, dynamic>? _stats;
  Map<String, dynamic>? _occupancy;
  List<dynamic>? _recentActivity;

  @override
  void initState() {
    super.initState();
    if (widget.loadInitialData) {
      _fetchStats();
      _fetchOccupancy();
      _fetchRecentActivity();
    }
  }

  Future<void> _fetchOccupancy() async {
    try {
      final remoteData = RemoteDataSource();
      final occupancy = await remoteData.getOccupancyCount();
      if (mounted) setState(() => _occupancy = occupancy);
    } catch (e) {
      if (mounted) setState(() => _occupancy = null);
    }
  }

  Future<void> _fetchStats() async {
    try {
      final remoteData = RemoteDataSource();
      final stats = await remoteData.getStats();
      if (mounted) setState(() => _stats = stats);
    } catch (e) {
      if (mounted) setState(() => _stats = null);
    }
  }

  Future<void> _fetchRecentActivity() async {
    try {
      final remoteData = RemoteDataSource();
      final history = await remoteData.getHistory(limit: 5);
      if (mounted) setState(() => _recentActivity = history);
    } catch (e) {
      if (mounted) setState(() => _recentActivity = null);
    }
  }

  Future<void> _refreshAll() async {
    await Future.wait([_fetchStats(), _fetchOccupancy(), _fetchRecentActivity()]);
  }

  Future<void> _startVerification() async {
    setState(() => _isLoading = true);
    try {
      final remoteData = RemoteDataSource();
      final sessionId = await remoteData.startSession();

      if (mounted) {
        Navigator.of(
          context,
        ).push(AppPageRoute.push(CameraView(sessionId: sessionId))).then((_) {
          _refreshAll();
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
            action: widget.onOpenSettings != null
                ? SnackBarAction(
                    label: 'Configure',
                    textColor: context.colors.primary,
                    onPressed: widget.onOpenSettings!,
                  )
                : null,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        showAppErrorSnackBar(
          context,
          'Something went wrong. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildDashboard() {
    final colors = context.colors;
    return RefreshIndicator(
      onRefresh: _refreshAll,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AppSurface(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
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
                  const SizedBox(height: 14),
                  Text(
                    _stats?["operator_name"] ?? "Door Staff",
                    style: TextStyle(
                      color: colors.ink,
                      fontSize: 26,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.01,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    DateFormat('EEEE, MMMM d').format(DateTime.now()),
                    style: TextStyle(
                      color: colors.muted,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildOccupancyCard(colors),
            const SizedBox(height: 16),
            AppSurface(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 20),
              child: Row(
                children: [
                  _buildStatColumn(
                    colors,
                    'Verified',
                    _stats != null ? _stats!["verified"].toString() : '-',
                    colors.ink,
                    isFirst: true,
                  ),
                  _buildStatColumn(
                    colors,
                    'Pending',
                    _stats != null ? _stats!["pending"].toString() : '-',
                    colors.ink,
                  ),
                  _buildStatColumn(
                    colors,
                    'Flagged',
                    _stats != null ? _stats!["flagged"].toString() : '-',
                    colors.warning,
                    isLast: true,
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
                        Icon(
                          Icons.document_scanner_rounded,
                          color: colors.onPrimary,
                        ),
                        const SizedBox(width: 10),
                        Text(
                          'Start Verification',
                          style: TextStyle(color: colors.onPrimary),
                        ),
                      ],
                    ),
            ),
            const SizedBox(height: 28),
            _buildRecentActivity(colors),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivity(AppColorsExt colors) {
    if (_recentActivity == null || _recentActivity!.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'RECENT ACTIVITY',
          style: TextStyle(
            color: colors.muted,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.06,
          ),
        ),
        const SizedBox(height: 10),
        AppSurface(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          child: Column(
            children: [
              for (int i = 0; i < _recentActivity!.length; i++) ...[
                if (i > 0) Divider(color: colors.line, height: 1),
                _buildActivityRow(colors, _recentActivity![i]),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActivityRow(AppColorsExt colors, dynamic item) {
    final decision = (item['final_decision'] ?? 'pending').toString();
    final statusColor = _statusColor(decision, colors);
    final statusIcon = _statusIcon(decision);
    final date = DateTime.tryParse(item['created_at'] ?? '');
    final formattedTime = date != null ? DateFormat('HH:mm').format(date) : '—';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 16),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              decision.toUpperCase(),
              style: TextStyle(
                color: colors.ink,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            formattedTime,
            style: TextStyle(
              color: colors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Color _statusColor(String decision, AppColorsExt colors) {
    switch (decision) {
      case 'pass':
        return colors.success;
      case 'check':
        return colors.warning;
      case 'deny':
      case 'block':
      case 'blocked':
        return colors.danger;
      default:
        return colors.muted;
    }
  }

  IconData _statusIcon(String decision) {
    switch (decision) {
      case 'pass':
        return Icons.check_rounded;
      case 'check':
        return Icons.help_outline_rounded;
      case 'deny':
      case 'block':
      case 'blocked':
        return Icons.block_rounded;
      default:
        return Icons.schedule_rounded;
    }
  }

  Widget _buildOccupancyCard(AppColorsExt colors) {
    final currentCount = _occupancy?['current_count'];
    final maxCapacity = _occupancy?['max_capacity'];
    final atCapacity = _occupancy?['at_capacity'] == true;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () {
          HapticFeedback.selectionClick();
          Navigator.of(context).push(AppPageRoute.push(const OccupancyView()));
        },
        child: AppSurface(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: (atCapacity ? colors.danger : colors.primary)
                      .withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.groups_rounded,
                  color: atCapacity ? colors.danger : colors.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Currently Inside',
                      style: TextStyle(
                        color: colors.muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      currentCount != null
                          ? (maxCapacity != null
                                ? '$currentCount / $maxCapacity'
                                : '$currentCount')
                          : '—',
                      style: TextStyle(
                        color: atCapacity ? colors.danger : colors.ink,
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              if (atCapacity)
                Text(
                  'AT CAPACITY',
                  style: TextStyle(
                    color: colors.danger,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                )
              else
                Icon(
                  Icons.chevron_right_rounded,
                  color: colors.muted,
                  size: 20,
                ),
            ],
          ),
        ),
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
      subtitle: _stats?["venue_name"] as String? ?? 'Door team verification',
      actions: [
        IconButton(
          tooltip: 'Refresh',
          icon: const Icon(Icons.sync_rounded),
          onPressed: _refreshAll,
        ),
      ],
      child: _buildDashboard(),
    );
  }
}
