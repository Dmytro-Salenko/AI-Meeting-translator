import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/meeting_screen.dart';
import 'screens/meeting_detail_screen.dart';
import 'screens/archive_screen.dart';
import 'core/theme/app_theme.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Meeting Translator',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkOnyxTheme,
      initialRoute: '/',
      onGenerateRoute: (settings) {
        switch (settings.name) {
          case '/':
            return MaterialPageRoute(builder: (context) => const HomeScreen());
          case '/meeting':
            return MaterialPageRoute(builder: (context) => const MeetingScreen());
          case '/details':
            final String meetingId = (settings.arguments as String?) ?? 'default';
            return MaterialPageRoute(
              builder: (context) => MeetingDetailScreen(meetingId: meetingId),
            );
          case '/archive':
            return MaterialPageRoute(builder: (context) => const ArchiveScreen());
          default:
            return MaterialPageRoute(builder: (context) => const HomeScreen());
        }
      },
    );
  }
}
