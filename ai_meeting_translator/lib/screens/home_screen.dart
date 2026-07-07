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
                  height: 220,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Left soundwave
                      _buildWaveformSide(isLeft: true),
                      const SizedBox(width: 20),
                      // Circular Mic Button container - Active start tap (Enlarged)
                      GestureDetector(
                        onTap: _startMeeting,
                        child: Container(
                          width: 140,
                          height: 140,
                          decoration: BoxDecoration(
                            color: const Color(0xFF16171D),
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: const Color(0xFF7F3DFF).withOpacity(0.4),
                              width: 2.0,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF7F3DFF).withOpacity(0.2),
                                blurRadius: 35,
                                spreadRadius: 4,
                              )
                            ],
                          ),
                          child: const Icon(
                            Icons.mic_rounded,
                            color: Color(0xFF7F3DFF),
                            size: 64, // Enlarged microphone icon
                          ),
                        ),
                      ),
                      const SizedBox(width: 20),
                      // Right soundwave
                      _buildWaveformSide(isLeft: false),
                    ],
                  ),
                ),
              ),
              const Spacer(),

              // 3. Archive Button (Enlarged, centered, and premium typography)
              GestureDetector(
                onTap: () {
                  Navigator.pushNamed(context, '/archive');
                },
                child: Container(
                  height: 64, // Enlarged height
                  decoration: BoxDecoration(
                    color: const Color(0xFF16171D), // Dark Card graphite matching image 1
                    borderRadius: BorderRadius.circular(16.0),
                    border: Border.all(color: Colors.white.withOpacity(0.06)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center, // Centered horizontally
                    crossAxisAlignment: CrossAxisAlignment.center, // Centered vertically
                    children: const [
                      Icon(Icons.folder_open_outlined, color: Colors.white, size: 24),
                      SizedBox(width: 12),
                      Text(
                        "Archive",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 18.0, // Larger text size
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: 0.1,
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
    // 9 symmetrical diamond-profile bars exactly matching the close-up reference image
    final List<double> heights = [12.0, 24.0, 42.0, 58.0, 78.0, 58.0, 42.0, 24.0, 12.0];

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: List.generate(heights.length, (index) {
        final double baseHeight = heights[index];
        return AnimatedBuilder(
          animation: _waveController,
          builder: (context, child) {
            // Symmetrical pulse animation
            final double animatedHeight = baseHeight + (_waveController.value * (baseHeight * 0.25));
            return Container(
              width: 3.0,
              height: animatedHeight,
              margin: const EdgeInsets.symmetric(horizontal: 2.5),
              decoration: BoxDecoration(
                color: const Color(0xFF7F3DFF).withOpacity(0.3 + (index == 4 ? 0.5 : (index % 3) * 0.15)),
                borderRadius: BorderRadius.circular(5),
              ),
            );
          },
        );
      }).toList(),
    );
  }
}
