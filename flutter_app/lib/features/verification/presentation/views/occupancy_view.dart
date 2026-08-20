import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../data/datasources/remote_data_source.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/empty_state.dart';

class OccupancyView extends StatefulWidget {
  const OccupancyView({super.key});

  @override
  State<OccupancyView> createState() => _OccupancyViewState();
}

class _OccupancyViewState extends State<OccupancyView> {
  bool _isLoading = true;
  List<dynamic> _occupants = [];
  Map<String, dynamic>? _count;
  String? _error;
  int? _checkingOutId;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _fetch();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => _fetch());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetch() async {
    try {
      final remoteData = RemoteDataSource();
      final results = await Future.wait([
        remoteData.getCurrentOccupants(),
        remoteData.getOccupancyCount(),
      ]);
      if (mounted) {
        setState(() {
          _occupants = results[0] as List<dynamic>;
          _count = results[1] as Map<String, dynamic>;
          _isLoading = false;
          _error = null;
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

  Future<void> _banAndAlert(Map<String, dynamic> occupant) async {
    final colors = context.colors;
    final reasonController = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: colors.surface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: Text(
            'Ban ${occupant['customer_name']}?',
            style: TextStyle(color: colors.ink),
          ),
          content: TextField(
            controller: reasonController,
            autofocus: true,
            decoration: const InputDecoration(labelText: 'Reason'),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () =>
                  Navigator.of(dialogContext).pop(reasonController.text.trim()),
              child: Text(
                'Confirm Ban & Alert',
                style: TextStyle(
                  color: colors.danger,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        );
      },
    );

    if (reason == null || reason.isEmpty || !mounted) return;

    try {
      final result = await RemoteDataSource().createBan(
        occupant['customer_id'] as int,
        reason,
      );
      if (!mounted) return;
      HapticFeedback.heavyImpact();
      final currentlyInside = result['currently_inside'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            currentlyInside
                ? '${occupant['customer_name']} banned. Alert broadcast — escort in progress.'
                : '${occupant['customer_name']} banned.',
          ),
        ),
      );
      await _fetch();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Could not ban: $e')));
      }
    }
  }

  Future<void> _checkOut(Map<String, dynamic> occupant) async {
    final id = occupant['occupancy_id'] as int;
    setState(() => _checkingOutId = id);
    try {
      await RemoteDataSource().checkOutOccupant(id);
      HapticFeedback.mediumImpact();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${occupant['customer_name']} checked out.')),
        );
      }
      await _fetch();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Could not check out: $e')));
      }
    } finally {
      if (mounted) setState(() => _checkingOutId = null);
    }
  }

  Widget _scrollableEmptyState(Widget child) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: child,
          ),
        );
      },
    );
  }

  Widget _buildCountHeader(BuildContext context) {
    final colors = context.colors;
    final current = _count?['current_count'] ?? 0;
    final maxCapacity = _count?['max_capacity'];
    final atCapacity = _count?['at_capacity'] == true;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
      margin: const EdgeInsets.fromLTRB(20, 4, 20, 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colors.surfaceRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: atCapacity
              ? colors.danger.withValues(alpha: 0.5)
              : colors.line,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.groups_rounded,
            color: atCapacity ? colors.danger : colors.primary,
            size: 32,
          ),
          const SizedBox(width: 16),
          Column(
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
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 220),
                transitionBuilder: (child, animation) => FadeTransition(
                  opacity: animation,
                  child: SlideTransition(
                    position: Tween<Offset>(
                      begin: const Offset(0, 0.3),
                      end: Offset.zero,
                    ).animate(animation),
                    child: child,
                  ),
                ),
                child: Text(
                  maxCapacity != null ? '$current / $maxCapacity' : '$current',
                  key: ValueKey('$current-$maxCapacity'),
                  style: TextStyle(
                    color: atCapacity ? colors.danger : colors.ink,
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          if (atCapacity) ...[
            const Spacer(),
            Text(
              'AT CAPACITY',
              style: TextStyle(
                color: colors.danger,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ] else ...[
            const Spacer(),
            Text(
              'Auto-checkout after ${_count?['occupancy_auto_expire_hours'] ?? 6}h',
              style: TextStyle(
                color: colors.muted,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    if (d.inHours >= 1) return '${d.inHours}h ${d.inMinutes % 60}m';
    return '${d.inMinutes}m';
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    Widget content;
    if (_isLoading) {
      content = _scrollableEmptyState(
        const Center(child: CircularProgressIndicator()),
      );
    } else if (_error != null) {
      content = _scrollableEmptyState(
        EmptyState(
          icon: Icons.error_outline_rounded,
          title: 'Occupancy unavailable',
          message: _error!,
          color: colors.danger,
        ),
      );
    } else if (_occupants.isEmpty) {
      content = Column(
        children: [
          _buildCountHeader(context),
          Expanded(
            child: _scrollableEmptyState(
              EmptyState(
                icon: Icons.groups_outlined,
                title: 'No one is currently inside',
                message:
                    'Approved visitors will appear here until checked out.',
                color: colors.primary,
              ),
            ),
          ),
        ],
      );
    } else {
      content = ListView.separated(
        padding: const EdgeInsets.fromLTRB(0, 0, 0, 20),
        itemCount: _occupants.length + 1,
        separatorBuilder: (context, index) => index == 0
            ? const SizedBox.shrink()
            : Divider(color: colors.line, height: 1, indent: 20, endIndent: 20),
        itemBuilder: (context, index) {
          if (index == 0) return _buildCountHeader(context);
          final occupant = _occupants[index - 1] as Map<String, dynamic>;
          final minutesInside = occupant['minutes_inside'];
          final isCheckingOut = _checkingOutId == occupant['occupancy_id'];

          final autoExpireAtRaw = occupant['auto_expire_at'] as String?;
          DateTime? autoExpireAt;
          Duration? timeRemaining;
          if (autoExpireAtRaw != null) {
            autoExpireAt = DateTime.tryParse(autoExpireAtRaw);
            if (autoExpireAt != null) {
              timeRemaining = autoExpireAt.difference(DateTime.now().toUtc());
            }
          }
          final isNearExpiry =
              timeRemaining != null &&
              timeRemaining.inMinutes <= 30 &&
              timeRemaining.inMinutes >= 0;
          final isOverdue =
              timeRemaining != null && timeRemaining.inMinutes < 0;

          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        (occupant['customer_name'] as String?) ?? 'Unknown',
                        style: TextStyle(
                          color: colors.ink,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        minutesInside != null
                            ? '$minutesInside min inside'
                            : '—',
                        style: TextStyle(
                          color: colors.muted,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (timeRemaining != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          isOverdue
                              ? 'Auto-checkout overdue'
                              : 'Auto-checkout in ${_formatDuration(timeRemaining)}',
                          style: TextStyle(
                            color: isOverdue || isNearExpiry
                                ? colors.danger
                                : colors.muted,
                            fontSize: 11,
                            fontWeight: isOverdue || isNearExpiry
                                ? FontWeight.w700
                                : FontWeight.w500,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                TextButton.icon(
                  onPressed: () => _banAndAlert(occupant),
                  icon: Icon(
                    Icons.block_rounded,
                    size: 16,
                    color: colors.danger,
                  ),
                  label: Text(
                    'Ban & Alert',
                    style: TextStyle(color: colors.danger),
                  ),
                ),
                TextButton.icon(
                  onPressed: isCheckingOut ? null : () => _checkOut(occupant),
                  icon: const Icon(Icons.logout_rounded, size: 16),
                  label: Text(isCheckingOut ? 'Checking out...' : 'Check Out'),
                ),
              ],
            ),
          );
        },
      );
    }

    return AppPage(
      title: 'Occupancy',
      subtitle: 'Who is currently inside',
      actions: [
        IconButton(
          icon: const Icon(Icons.refresh_rounded),
          onPressed: () {
            setState(() => _isLoading = true);
            _fetch();
          },
        ),
      ],
      child: RefreshIndicator(onRefresh: _fetch, child: content),
    );
  }
}
