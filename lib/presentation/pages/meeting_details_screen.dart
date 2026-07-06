import 'dart:ui';
import 'package:flutter/material.dart';
import '../widgets/speaker_management_sheet.dart';

class MeetingDetailsScreen extends StatefulWidget {
  final String meetingId;
  const MeetingDetailsScreen({Key? key, required this.meetingId}) : super(key: key);

  @override
  State<MeetingDetailsScreen> createState() => _MeetingDetailsScreenState();
}

class _MeetingDetailsScreenState extends State<MeetingDetailsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  double _currentAudioPosition = 0.0;
  final double _totalAudioDuration = 18.0;

  // Mock Meeting Transcript Segments
  final List<Map<String, dynamic>> _segments = [
    {
      "speaker": "Speaker A",
      "time": "0:00",
      "seconds": 0.0,
      "text": "Hello everyone, thank you for joining this sync. Today we need to decide on our cloud storage provider.",
      "translation": "Привет всем, спасибо что присоединились к этой встрече. Сегодня нам нужно определиться с провайдером облачного хранилища."
    },
    {
      "speaker": "Speaker B",
      "time": "0:05",
      "seconds": 5.0,
      "text": "I think we should proceed with Cloudflare R2 due to its zero egress fees and full S3 compatibility.",
      "translation": "Я думаю, нам стоит остановиться на Cloudflare R2 из-за нулевой платы за исходящий трафик и полной совместимости с S3."
    },
    {
      "speaker": "Speaker A",
      "time": "0:10",
      "seconds": 10.0,
      "text": "That makes total sense. Let's make that decision official. Dmitry, please set up the S3StorageProvider adapter.",
      "translation": "В этом есть полный смысл. Давайте зафиксируем это решение. Дмитрий, пожалуйста, настройте адаптер S3StorageProvider."
    },
    {
      "speaker": "Speaker B",
      "time": "0:15",
      "seconds": 15.0,
      "text": "Will do. I will also check the database indices to make sure full-text search works.",
      "translation": "Сделаю. Я также проверю индексы базы данных, чтобы убедиться в корректности полнотекстового поиска."
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

  void _seekTo(double seconds) {
    setState(() {
      _currentAudioPosition = seconds.clamp(0.0, _totalAudioDuration);
    });
  }

  void _openSpeakerManagement(String currentName) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return SpeakerManagementSheet(
          speakerName: currentName,
          onRename: (newName) {
            // In production, trigger meeting segment / speaker updates
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Переименовано в $newName")),
            );
          },
          onMerge: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text("Запущено слияние спикеров")),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "Встреча: Облачное хранилище",
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
                // 1. Sliding Segmented Controller
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
                      fontFamily: 'Inter', 
                      fontSize: 14.0, 
                      fontWeight: FontWeight.w600
                    ),
                    unselectedLabelColor: Colors.white60,
                    labelColor: Colors.white,
                    tabs: const [
                      Tab(text: "Стенограмма"),
                      Tab(text: "AI Саммари"),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // 2. Tab Views
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildTranscriptTab(),
                      _buildSummaryTab(),
                    ],
                  ),
                ),
                // Padding for floating player
                const SizedBox(height: 120),
              ],
            ),
          ),
          
          // 3. Floating Frosted Media Player Overlay
          Align(
            alignment: Alignment.bottomCenter,
            child: _buildFrostedMediaPlayer(),
          )
        ],
      ),
    );
  }

  Widget _buildTranscriptTab() {
    return ListView.builder(
      physics: const BouncingScrollPhysics(),
      itemCount: _segments.length,
      itemBuilder: (context, index) {
        final seg = _segments[index];
        final bool isCurrent = _currentAudioPosition >= seg["seconds"] &&
            (index == _segments.length - 1 || _currentAudioPosition < _segments[index + 1]["seconds"]);

        return GestureDetector(
          onTap: () => _seekTo(seg["seconds"]),
          child: Container(
            margin: const EdgeInsets.only(bottom: 16.0),
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              color: isCurrent ? const Color(0xFF22232B) : const Color(0xFF16171D),
              borderRadius: BorderRadius.circular(16.0),
              border: Border.all(
                color: isCurrent ? Colors.white12 : Colors.transparent,
                width: 1.0,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.between,
                  children: [
                    GestureDetector(
                      onTap: () => _openSpeakerManagement(seg["speaker"]),
                      child: Text(
                        seg["speaker"],
                        style: const TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14.0,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF3B82F6),
                        ),
                      ),
                    ),
                    Text(
                      seg["time"],
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12.0,
                        color: Colors.white38,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  seg["translation"],
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 16.0,
                    height: 1.5,
                    color: isCurrent ? Colors.white : Colors.white90,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  seg["text"],
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 14.0,
                    height: 1.4,
                    color: Colors.white30,
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
          _buildSummarySection(
            "Краткое содержание",
            "На встрече обсудили переход на Cloudflare R2 в качестве основного объектного хранилища. Опция была выбрана ввиду полного соответствия API S3 и отсутствия платы за транзит исходящих данных (egress fees), что существенно снижает бюджет инфраструктуры.",
            Colors.blueAccent,
          ),
          _buildSummarySection(
            "Основные решения",
            "• Принять Cloudflare R2 как стандарт хранения аудио.\n• Развернуть PostgreSQL/Supabase схему с полнотекстовыми индексами.",
            Colors.emerald,
          ),
          _buildSummarySection(
            "Задачи (Action Items)",
            "• Дмитрий $\\rightarrow$ Реализовать S3StorageProvider адаптер на бэкенде.\n• AI Агент $\\rightarrow$ Проверить работу миграций и индексов БД.",
            Colors.orangeAccent,
          ),
          _buildSummarySection(
            "Открытые вопросы",
            "• Каковы ограничения провайдера Modal на пиковые параллельные вызовы STT-моделей?",
            Colors.purpleAccent,
          ),
        ],
      ),
    );
  }

  Widget _buildSummarySection(String title, String content, Color markerColor) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: const Color(0xFF16171D),
        borderRadius: BorderRadius.circular(16.0),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Vertical Accent Left-Border Marker
          Container(
            width: 4,
            height: 40,
            decoration: BoxDecoration(
              color: markerColor,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 15.0,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  content,
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 14.0,
                    height: 1.5,
                    color: Colors.white70,
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildFrostedMediaPlayer() {
    return Container(
      margin: const EdgeInsets.all(16.0),
      height: 90,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24.0),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 15.0, sigmaY: 15.0),
          child: Container(
            color: const Color(0xFF16171D).withOpacity(0.7),
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.play_arrow, color: Colors.white, size: 36),
                  onPressed: () {},
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Linear Waveform Seekbar emulator
                      Slider(
                        value: _currentAudioPosition,
                        max: _totalAudioDuration,
                        activeColor: Colors.white,
                        inactiveColor: Colors.white24,
                        onChanged: (val) => _seekTo(val),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.between,
                          children: [
                            Text(
                              "0:${_currentAudioPosition.toInt().toString().padLeft(2, '0')}",
                              style: const TextStyle(color: Colors.white38, fontSize: 11),
                            ),
                            Text(
                              "0:${_totalAudioDuration.toInt()}",
                              style: const TextStyle(color: Colors.white38, fontSize: 11),
                            ),
                          ],
                        ),
                      )
                    ],
                  ),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}
