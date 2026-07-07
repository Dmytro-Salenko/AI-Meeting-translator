import 'dart:async';
import 'package:flutter/material.dart';

class MeetingActiveScreen extends StatefulWidget {
  const MeetingActiveScreen({Key? key}) : super(key: key);

  @override
  State<MeetingActiveScreen> createState() => _MeetingActiveScreenState();
}

class _MeetingActiveScreenState extends State<MeetingActiveScreen> {
  final ScrollController _scrollController = ScrollController();
  late Timer _timer;
  int _secondsElapsed = 0;
  
  // Simulated streaming translator text blocks (Russian)
  final List<String> _translationParagraphs = [
    "Начало встречи. Распознавание запущено...",
  ];

  late Timer _mockDataTimer;
  int _mockSentenceIndex = 0;

  final List<String> _mockSentences = [
    "Приветствую команду. Давайте обсудим дедлайны по интеграции платежной системы.",
    "Нам необходимо закончить тестирование API к следующему четвергу, чтобы уложиться в спринт.",
    "Дмитрий, подскажи, пожалуйста, готовы ли схемы базы данных на Supabase?",
    "Отлично. Также не забываем про кэш надежности на клиенте во избежание сбоев сети.",
    "На этом синхронизацию завершаем. Всем спасибо за участие."
  ];

  @override
  void initState() {
    super.initState();
    // Meeting duration timer (1Hz)
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _secondsElapsed++;
      });
    });

    // Simulate incoming translation chunks via WebSocket (simulates neural response)
    _mockDataTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      if (_mockSentenceIndex < _mockSentences.length) {
        setState(() {
          _translationParagraphs.add(_mockSentences[_mockSentenceIndex]);
          _mockSentenceIndex++;
        });
        _scrollToBottom();
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    _mockDataTimer.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  String _formatDuration(int totalSeconds) {
    final int hours = totalSeconds ~/ 3600;
    final int minutes = (totalSeconds % 3600) ~/ 60;
    final int seconds = totalSeconds % 60;
    return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  void _stopMeeting() {
    // Navigate to processing/details or pop back
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF000000), // OLED Pure Black
      body: SafeArea(
        child: Column(
          children: [
            // 1. Status Bar: pulsing recording dot & counter
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      _buildPulseRecordingDot(),
                      const SizedBox(width: 8),
                      const Text(
                        "ЗАПИСЬ",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 12.0,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFFEF4444),
                          letterSpacing: 1.0,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    _formatDuration(_secondsElapsed),
                    style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 16.0,
                      fontWeight: FontWeight.w600,
                      color: Colors.white70,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),

            // 2. Main Live Translation Area with Fade-Out Mask
            Expanded(
              child: ShaderMask(
                shaderCallback: (Rect bounds) {
                  return const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black,
                    ],
                    stops: [0.0, 0.15],
                  ).createShader(bounds);
                },
                blendMode: BlendMode.dstIn,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: ListView.builder(
                    controller: _scrollController,
                    physics: const BouncingScrollPhysics(),
                    itemCount: _translationParagraphs.length,
                    itemBuilder: (context, index) {
                      final item = _translationParagraphs[index];
                      return TweenAnimationBuilder<double>(
                        tween: Tween<double>(begin: 0.0, end: 1.0),
                        duration: const Duration(milliseconds: 600),
                        builder: (context, opacityValue, child) {
                          return Opacity(
                            opacity: opacityValue,
                            child: Padding(
                              padding: const EdgeInsets.only(bottom: 24.0),
                              child: Text(
                                item,
                                style: const TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 22.0,
                                  height: 1.65,
                                  fontWeight: FontWeight.w400,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ),

            // 3. Stop Control Panel (Rounded Square)
            Padding(
              padding: const EdgeInsets.only(bottom: 32.0, top: 16.0),
              child: Center(
                child: RawMaterialButton(
                  onPressed: _stopMeeting,
                  elevation: 2.0,
                  fillColor: const Color(0xFFEF4444),
                  padding: const EdgeInsets.all(24.0),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(
                    Icons.stop,
                    color: Colors.white,
                    size: 32.0,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPulseRecordingDot() {
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.3, end: 1.0),
      duration: const Duration(seconds: 1),
      curve: Curves.easeInOut,
      builder: (context, value, child) {
        return Opacity(
          opacity: value,
          child: Container(
            width: 10,
            height: 10,
            decoration: const BoxDecoration(
              color: Color(0xFFEF4444),
              shape: BoxShape.circle,
            ),
          ),
        );
      },
    );
  }
}
