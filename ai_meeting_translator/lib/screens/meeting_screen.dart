import 'dart:async';
import 'package:flutter/material.dart';

class MeetingScreen extends StatefulWidget {
  const MeetingScreen({Key? key}) : super(key: key);

  @override
  State<MeetingScreen> createState() => _MeetingScreenState();
}

class _MeetingScreenState extends State<MeetingScreen> {
  final ScrollController _scrollController = ScrollController();
  late Timer _timer;
  int _secondsElapsed = 0;
  
  final List<String> _paragraphs = [
    "Сессия инициализирована. Запуск WebSocket...",
  ];

  late Timer _mockDataTimer;
  int _mockIndex = 0;
  final List<String> _mockTexts = [
    "Здравствуйте. Начнем обсуждение новой архитектуры поиска.",
    "Мы планируем использовать ИИ-агента для разбора трилингвальных запросов.",
    "Это позволит пользователям писать вопросы на русском, украинском и английском языках.",
    "Система автоматически найдет нужные аудиосегменты и покажет таймкоды.",
    "На сегодня все. Завершаем встречу и отправляем на постобработку."
  ];

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _secondsElapsed++;
      });
    });

    _mockDataTimer = Timer.periodic(const Duration(seconds: 3), (timer) {
      if (_mockIndex < _mockTexts.length) {
        setState(() {
          _paragraphs.add(_mockTexts[_mockIndex]);
          _mockIndex++;
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
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  String _formatTime(int totalSecs) {
    final int h = totalSecs ~/ 3600;
    final int m = (totalSecs % 3600) ~/ 60;
    final int s = totalSecs % 60;
    return '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF000000), // Pure OLED black
      body: SafeArea(
        child: Column(
          children: [
            // Status bar
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: Color(0xFFEF4444),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        "🔴 ЗАПИСЬ ИДЕТ",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 12.0,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFFEF4444),
                        ),
                      ),
                    ],
                  ),
                  Text(
                    _formatTime(_secondsElapsed),
                    style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 16.0,
                      fontWeight: FontWeight.w600,
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),
            ),

            // Live text stream area
            Expanded(
              child: ShaderMask(
                shaderCallback: (bounds) {
                  return const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [Colors.transparent, Colors.black],
                    stops: [0.0, 0.15],
                  ).createShader(bounds);
                },
                blendMode: BlendMode.dstIn,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: ListView.builder(
                    controller: _scrollController,
                    physics: const BouncingScrollPhysics(),
                    itemCount: _paragraphs.length,
                    itemBuilder: (context, index) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 24.0),
                        child: Text(
                          _paragraphs[index],
                          style: const TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 22.0,
                            height: 1.65,
                            color: Colors.white,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),

            // Stop button
            Padding(
              padding: const EdgeInsets.only(bottom: 32.0, top: 16.0),
              child: RawMaterialButton(
                onPressed: () {
                  Navigator.pushReplacementNamed(context, '/details', arguments: 'meeting_demo');
                },
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
          ],
        ),
      ),
    );
  }
}
