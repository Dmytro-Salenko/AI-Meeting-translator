import 'package:flutter/material.dart';

class AppTheme {
  // Hex color codes mapped to Flutter Color objects
  static const Color darkCanvas = Color(0xFF0D0E12); // Deep Matte Black
  static const Color darkSurface = Color(0xFF16171D); // Dark Graphite Card background
  static const Color accentRed = Color(0xFFE53935); // Stop Floating Capsule Red

  static ThemeData get darkTheme {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: darkCanvas,
      cardColor: darkSurface,
      colorScheme: const ColorScheme.dark(
        primary: Colors.white,
        surface: darkSurface,
        error: accentRed,
      ),
      textTheme: const TextTheme(
        // Style specific to translation output (lineHeight 1.65, 20sp)
        bodyLarge: TextStyle(
          fontFamily: 'Inter',
          fontSize: 20.0,
          fontWeight: FontWeight.w400,
          height: 1.65,
          color: Colors.white,
        ),
        // Style for secondary labels/UI components
        bodyMedium: TextStyle(
          fontFamily: 'Inter',
          fontSize: 14.0,
          fontWeight: FontWeight.w400,
          color: Colors.white70,
        ),
      ),
    );
  }
}
