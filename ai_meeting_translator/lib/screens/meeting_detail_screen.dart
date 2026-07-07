import 'dart:ui';
import 'package:flutter/material.dart';

class MeetingDetailScreen extends StatefulWidget {
  final String meetingId;
  const MeetingDetailScreen({Key? key, required this.meetingId}) : super(key: key);

  @override
  State<MeetingDetailScreen> createState() => _MeetingDetailScreenState();
}

class _MeetingDetailScreenState extends State<MeetingDetailScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  double _audioPosition = 0.0;
  final double _audioLength = 15.0;

  final List<Map<String, dynamic>> _transcript = [
    {
      "speaker": "Speaker A (Dmitry)",
      "sec": 0.0,
      "time": "0:00",
      "text": "Здравствуйте. Начнем обсуждение новой архитектуры поиска.",
    },
    {
      "speaker": "Speaker B (David)",
      "sec": 3.0,
      "time": "0:03",
      "text": "Мы планируем использовать ИИ-агента для разбора трилингвальных запросов.",
    },
    {
      "speaker": "Speaker A (Dmitry)",
      "sec": 6.0,
      "time": "0:06",
      "text": "Это позволит пользователям писать вопросы на русском, украинском и английском языках.",
    },
    {
      "speaker": "Speaker B (David)",
      "sec": 9.0,
      "time": "0:09",
      "text": "Система автоматически найдет нужные аудиосегменты и покажет таймкоды.",
    },
    {
      "speaker": "Speaker A (Dmitry)",
      "sec": 12.0,
      "time": "0:12",
      "text": "На сегодня все. Завершаем встречу и отправляем на постобработку.",
    }
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "Встреча: Архитектура Поиска",
          style: TextStyle(fontFamily: 'Inter', fontSize: 18.0, fontWeight: FontWeight.w600),
        ),
      ),
      body: Stack(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Column(
              children: [
                const SizedBox(height: 8),
                // Metadata Block (Date, Time, Duration, Participants)
                Container(
                  padding: const EdgeInsets.all(16.0),
                  margin: const EdgeInsets.only(bottom: 12.0),
                  decoration: BoxDecoration(
                    color: const Color(0xFF16171D),
                    borderRadius: BorderRadius.circular(16.0),
                    border: Border.all(color: Colors.white.withOpacity(0.04)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: const [
                          Text("Дата: 2026-07-07", style: TextStyle(color: Colors.white70, fontFamily: 'Inter', fontSize: 13)),
                          Text("Время: 14:30 - 14:45", style: TextStyle(color: Colors.white70, fontFamily: 'Inter', fontSize: 13)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: const [
                          Text("Длительность: 15 минут", style: TextStyle(color: Colors.white70, fontFamily: 'Inter', fontSize: 13)),
                          Text("Участники: Dmitry, David", style: TextStyle(color: Color(0xFF3B82F6), fontFamily: 'Inter', fontSize: 13, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(4.0),
                  decoration: BoxDecoration(
                    color: const Color(0xFF16171D),
                    borderRadius: BorderRadius.circular(12.0),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicator: BoxDecoration(
                      color: const Color(0xFF2E2F38),
                      borderRadius: BorderRadius.circular(8.0),
                    ),
                    labelStyle: const TextStyle(
                        fontFamily: 'Inter', fontSize: 14.0, fontWeight: FontWeight.w600),
                    unselectedLabelColor: Colors.white60,
                    labelColor: Colors.white,
                    tabs: const [
                      Tab(text: "Стенограмма"),
                      Tab(text: "AI Саммари"),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildTranscriptTab(),
                      _buildSummaryTab(),
                    ],
                  ),
                ),
                const SizedBox(height: 120),
              ],
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: _buildAudioPlayer(),
          )
        ],
      ),
    );
  }

  Widget _buildTranscriptTab() {
    return ListView.builder(
      physics: const BouncingScrollPhysics(),
      itemCount: _transcript.length,
      itemBuilder: (context, index) {
        final seg = _transcript[index];
        final bool isPlaying = _audioPosition >= seg["sec"] &&
            (index == _transcript.length - 1 || _audioPosition < _transcript[index + 1]["sec"]);

        return GestureDetector(
          onTap: () {
            setState(() {
              _audioPosition = seg["sec"];
            });
          },
          child: Container(
            margin: const EdgeInsets.only(bottom: 12.0),
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              color: isPlaying ? const Color(0xFF22232B) : const Color(0xFF16171D),
              borderRadius: BorderRadius.circular(16.0),
              border: Border.all(
                color: isPlaying ? Colors.white10 : Colors.transparent,
                width: 1.0,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      seg["speaker"],
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 14.0,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF3B82F6),
                      ),
                    ),
                    Text(
                      seg["time"],
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12.0,
                        color: Colors.white30,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  seg["text"],
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 15.0,
                    height: 1.45,
                    color: isPlaying ? Colors.white : Colors.white.withOpacity(0.9),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSummaryTab() {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        children: [
          _buildSummaryBlock(
            "Краткое содержание",
            "Команда обсудила запуск трилингвального ИИ-агента поиска. Новая архитектура позволит вводить запросы на русском, украинском и английском языках, автоматически сопоставляя смысл с оригинальным текстом или переводами в базе данных.",
            Colors.blueAccent,
          ),
          _buildSummaryBlock(
            "Основные решения",
            "• Интегрировать OpenRouter (Gemini 2.5 Flash) для парсинга поисковых намерений.\n• Сохранить биометрические голосовые отпечатки для локального тестирования.",
            Colors.green,
          ),
          _buildSummaryBlock(
            "Задачи (Action Items)",
            "• Дмитрий \$\\rightarrow\$ Разработать API-эндпоинт поиска.\n• Давид \$\\rightarrow\$ Сверстать экран архива во Flutter.",
            Colors.orangeAccent,
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryBlock(String title, String body, Color marker) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: const Color(0xFF16171D),
        borderRadius: BorderRadius.circular(16.0),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 35,
            decoration: BoxDecoration(color: marker, borderRadius: BorderRadius.circular(2)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 6),
                Text(body, style: const TextStyle(color: Colors.white70, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAudioPlayer() {
    return Container(
      margin: const EdgeInsets.all(16.0),
      height: 90,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24.0),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10.0, sigmaY: 10.0),
          child: Container(
            color: const Color(0xFF16171D).withOpacity(0.8),
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.play_arrow, color: Colors.white, size: 36),
                  onPressed: () {},
                ),
                Expanded(
                  child: Slider(
                    value: _audioPosition,
                    max: _audioLength,
                    activeColor: Colors.white,
                    inactiveColor: Colors.white24,
                    onChanged: (val) {
                      setState(() {
                        _audioPosition = val;
                      });
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
