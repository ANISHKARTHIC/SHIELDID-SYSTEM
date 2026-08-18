import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'features/verification/presentation/views/home_view.dart';
import 'features/verification/presentation/views/history_view.dart';
import 'features/verification/presentation/views/notifications_view.dart';
import 'core/network/dio_client.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DioClient().init();
  runApp(const ProviderScope(child: PubEntryApp()));
}

class PubEntryApp extends StatelessWidget {
  final bool loadInitialData;

  const PubEntryApp({super.key, this.loadInitialData = true});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pub Entry Staff',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: MainNavigationScreen(loadInitialData: loadInitialData),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  final bool loadInitialData;

  const MainNavigationScreen({super.key, this.loadInitialData = true});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  late final List<Widget> _screens = [
    HomeView(loadInitialData: widget.loadInitialData),
    const HistoryView(),
    const NotificationsView(),
    const Center(child: Text("Profile & Settings")),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.line)),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) =>
              setState(() => _currentIndex = index),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.verified_user_outlined),
              selectedIcon: Icon(Icons.verified_user),
              label: 'Verify',
            ),
            NavigationDestination(
              icon: Icon(Icons.history_rounded),
              label: 'History',
            ),
            NavigationDestination(
              icon: Icon(Icons.notifications_none_rounded),
              selectedIcon: Icon(Icons.notifications_rounded),
              label: 'Alerts',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline_rounded),
              selectedIcon: Icon(Icons.person_rounded),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }
}
