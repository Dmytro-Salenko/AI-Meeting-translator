import 'package:flutter/material.dart';

class AppTheme {
  // Fluid Onyx color design system tokens
  static const Color onyxBackground = Color(0xFF121212); // Deep Charcoal Onyx
  static const Color onyxSurface = Color(0xFF1C1C24);    // Elevated Glassmorphism Graphite Cards
  static const Color onyxBorder = Color(0xFF2C2C35);     // Thin border separator
  
  // Status Accent Colors
  static const Color emeraldActive = Color(0xFF10B981);  // Recording active indicator
  static const Color amberWarning = Color(0xFFF59E0B);   // Network lost warning
  static const Color blueSync = Color(0xFF3B82F6);       // Buffer uploading/restoring
  static const Color stopRed = Color(0xFFEF4444);        // STOP Capsule background

  static ThemeData get darkOnyxTheme {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: onyxBackground,
      cardColor: onyxSurface,
      dividerColor: onyxBorder,
      colorScheme: const ColorScheme.dark(
        primary: Colors.white,
        secondary: blueSync,
        surface: onyxSurface,
        background: onyxBackground,
        error: stopRed,
      ),
      textTheme: const TextTheme(
        // High-contrast, spacious typography for live translation view
        bodyLarge: TextStyle(
          fontFamily: 'Inter',
          fontSize: 22.0,
          fontWeight: FontWeight.w400,
          height: 1.65,
          color: Colors.white,
          letterSpacing: 0.15,
        ),
        // Secondary description texts
        bodyMedium: TextStyle(
          fontFamily: 'Inter',
          fontSize: 14.0,
          color: Colors.white70,
          height: 1.4,
        ),
        // Titles and headers
        titleMedium: TextStyle(
          fontFamily: 'Inter',
          fontSize: 16.0,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      ),
    );
  }
}
