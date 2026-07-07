import 'package:flutter/material.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late AnimationController _waveController;

  @override
  void initState() {
    super.initState();
    // Animation for pulsing soundwave visualization
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _waveController.dispose();
    super.dispose();
  }

  void _startMeeting() {
    Navigator.pushNamed(context, '/meeting');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12), // Deep Matte Black Canvas
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. App Bar Header (Title Logo & Settings Gear icon)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        "AI Meeting",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 34.0, // Larger, more prominent logo
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                      Text(
                        "Translator",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 34.0, // Larger, more prominent logo
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF7F3DFF), // Violet Brand color
                          letterSpacing: -0.5,
                        ),
                      ),
                    ],
                  ),
                  // Small minimalistic settings icon on the top right
                  Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF16171D),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white.withOpacity(0.05)),
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.settings_outlined, color: Colors.white, size: 24),
                      onPressed: () {},
                    ),
                  ),
                ],
              ),
              const Spacer(),

              // 2. Central Mic Button & Soundwave Visualization (Active Trigger)
              Center(
                child: Container(
                  height: 200,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Left soundwave
                      _buildWaveformSide(isLeft: true),
                      const SizedBox(width: 16),
                      // Circular Mic Button container - Active start tap
                      GestureDetector(
                        onTap: _startMeeting,
                        child: Container(
                          width: 96,
                          height: 96,
                          decoration: BoxDecoration(
                            color: const Color(0xFF16171D),
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: const Color(0xFF7F3DFF).withOpacity(0.3),
                              width: 1.5,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF7F3DFF).withOpacity(0.15),
                                blurRadius: 25,
                                spreadRadius: 2,
                              )
                            ],
                          ),
                          child: const Icon(
                            Icons.mic_rounded,
                            color: Color(0xFF7F3DFF),
                            size: 42,
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      // Right soundwave
                      _buildWaveformSide(isLeft: false),
                    ],
                  ),
                ),
              ),
              const Spacer(),

              // 3. Violet Gradient Start Meeting Button
              GestureDetector(
                onTap: _startMeeting,
                child: Container(
                  height: 64,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF7F3DFF),
                        Color(0xFF9E66FF),
                      ],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
                    borderRadius: BorderRadius.circular(16.0),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF7F3DFF).withOpacity(0.3),
                        blurRadius: 15,
                        offset: const Offset(0, 4),
                      )
                    ],
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Icon(Icons.play_arrow_rounded, color: Colors.white, size: 26),
                      SizedBox(width: 8),
                      Text(
                        "Start Meeting",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 16.0,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // 4. Archive Button (Lighter background, larger and lighter text)
              GestureDetector(
                onTap: () {
                  Navigator.pushNamed(context, '/archive');
                },
                child: Container(
                  height: 56,
                  decoration: BoxDecoration(
                    color: const Color(0xFF2E2F38), // Lighter card grey matching specs
                    borderRadius: BorderRadius.circular(16.0),
                    border: Border.all(color: Colors.white.withOpacity(0.08)),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(
                    children: const [
                      Icon(Icons.folder_open_outlined, color: Colors.white, size: 22),
                      SizedBox(width: 14),
                      Text(
                        "Archive",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 16.0, // Larger text
                          fontWeight: FontWeight.w700, // Lighter, bold and clean text
                          color: Colors.white, // Fully white text
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const Spacer(),

              // 5. Security Footer
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.lock_outline_rounded, color: Colors.white.withOpacity(0.2), size: 14),
                  const SizedBox(width: 6),
                  Text(
                    "Локально и безопасно.\nВаши данные под защитой.",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11.0,
                      color: Colors.white.withOpacity(0.25),
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWaveformSide({required bool isLeft}) {
    return Row(
      children: List.generate(4, (index) {
        final double baseHeight = (index + 1) * 12.0;
        return AnimatedBuilder(
          animation: _waveController,
          builder: (context, child) {
            final double animatedHeight = baseHeight + (_waveController.value * 20.0);
            return Container(
              width: 3.5,
              height: animatedHeight.clamp(8.0, 70.0),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF7F3DFF).withOpacity(0.2 + (index * 0.15)),
                borderRadius: BorderRadius.circular(2),
              ),
            );
          },
        );
      }).toList(),
    );
  }
}
