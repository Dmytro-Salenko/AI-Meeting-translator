import 'package:flutter/material.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 40),
              const Text(
                "AI Meeting Translator",
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 24.0,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  letterSpacing: 0.5,
                ),
              ),
              const Spacer(),
              AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  return Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF10B981).withOpacity(0.1 + (_pulseController.value * 0.15)),
                          blurRadius: 35 + (_pulseController.value * 15),
                          spreadRadius: 5 + (_pulseController.value * 5),
                        )
                      ],
                    ),
                    child: child,
                  );
                },
                child: RawMaterialButton(
                  onPressed: () {
                    Navigator.pushNamed(context, '/meeting');
                  },
                  fillColor: const Color(0xFF16171D),
                  padding: const EdgeInsets.all(48.0),
                  shape: const CircleBorder(
                    side: BorderSide(color: Color(0xFF2C2C35), width: 1),
                  ),
                  child: const Icon(
                    Icons.mic_none_outlined,
                    color: Color(0xFF10B981),
                    size: 56.0,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                "Начать запись",
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 16.0,
                  fontWeight: FontWeight.w600,
                  color: Colors.white70,
                ),
              ),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.pushNamed(context, '/archive');
                },
                icon: const Icon(Icons.archive_outlined, size: 20),
                label: const Text(
                  "Открыть архив",
                  style: TextStyle(fontFamily: 'Inter', fontWeight: FontWeight.w600),
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: const BorderSide(color: Color(0xFF2C2C35)),
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 18),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
