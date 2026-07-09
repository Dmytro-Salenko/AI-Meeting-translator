import 'dart:async';
import 'package:flutter/material.dart';
import '../services/socket_service.dart';
import '../services/api_service.dart';

class MeetingScreen extends StatefulWidget {
  const MeetingScreen({Key? key}) : super(key: key);

  @override
  State<MeetingScreen> createState() => _MeetingScreenState();
}

class SpeechSegment {
  final String speakerInitials;
  final String timestamp;
  final String text;
  final Color color;

  SpeechSegment({
    required this.speakerInitials,
    required this.timestamp,
    required this.text,
    required this.color,
  });
}

class _MeetingScreenState extends State<MeetingScreen> {
  final ScrollController _scrollController = ScrollController();
  final SocketService _socketService = SocketService();
  final ApiService _apiService = ApiService();
  StreamSubscription? _translationSubscription;
  late Timer _timer;
  int _secondsElapsed = 0;

  final List<SpeechSegment> _segments = [
    SpeechSegment(
      speakerInitials: "C",
      timestamp: "00:21",
      text: "Итак, давайте начнем с ключевых целей на этот квартал. Наша основная задача — увеличить удовлетворенность клиентов и сократить время ответа поддержки.",
      color: const Color(0xFF7F3DFF), // Purple
    ),
  ];

  late Timer _mockDataTimer;
  int _mockIndex = 0;
  final List<SpeechSegment> _mockSegments = [
    SpeechSegment(
      speakerInitials: "M",
      timestamp: "00:32",
      text: "Мы также обсудим запуск новой функции и план маркетинговых активностей на следующий месяц.",
      color: const Color(0xFF3B82F6), // Blue
    ),
    SpeechSegment(
      speakerInitials: "A",
      timestamp: "00:47",
      text: "Есть ли вопросы по первому пункту?",
      color: const Color(0xFFEF4444), // Amber/Orange
    ),
    SpeechSegment(
      speakerInitials: "S",
      timestamp: "01:05",
      text: "Да, подскажите, какие метрики поддержки мы будем считать основными?",
      color: const Color(0xFFF59E0B), // Orange
    )
  ];

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _secondsElapsed++;
      });
    });

    // Start WebSocket Live transcription sync
    final String mockMeetingId = "meeting_${DateTime.now().millisecondsSinceEpoch}";
    _socketService.connect(mockMeetingId);
    _socketService.startRecordingAndStreaming();

    _translationSubscription = _socketService.translationStream.listen((translation) {
      setState(() {
        _segments.add(SpeechSegment(
          speakerInitials: "C",
          timestamp: _formatTime(_secondsElapsed).substring(3),
          text: translation,
          color: const Color(0xFF7F3DFF),
        ));
      });
      _scrollToBottom();
    });

    _mockDataTimer = Timer.periodic(const Duration(seconds: 8), (timer) {
      if (_mockIndex < _mockSegments.length) {
        setState(() {
          _segments.add(_mockSegments[_mockIndex]);
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
    _translationSubscription?.cancel();
    _socketService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        // Only auto-scroll to the bottom if the user is already near the bottom (within 120 pixels threshold).
        // This allows them to scroll back and read earlier translation text without focus hijack.
        final double maxScroll = _scrollController.position.maxScrollExtent;
        final double currentScroll = _scrollController.offset;
        const double threshold = 120.0;
        
        if (maxScroll - currentScroll <= threshold) {
          _scrollController.animateTo(
            maxScroll,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
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
      backgroundColor: const Color(0xFF0D0E12), // OLED deep dark
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Top Recording Status Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
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
                        "Запись активна",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14.0,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    _formatTime(_secondsElapsed),
                    style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 14.0,
                      fontWeight: FontWeight.w600,
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),
            ),

            // 2. Participants Horizontal Bar (T3)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Участники (нажмите для подписания)",
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 12.0,
                      color: Colors.white38,
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 80,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      children: [
                        _buildParticipantAvatar("C", const Color(0xFF7F3DFF)),
                        _buildParticipantAvatar("M", const Color(0xFF3B82F6)),
                        _buildParticipantAvatar("A", const Color(0xFF10B981)),
                        _buildParticipantAvatar("S", const Color(0xFFF59E0B)),
                        _buildParticipantAvatar("D", const Color(0xFF2563EB)),
                        _buildMoreAvatar("+2"),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 3. Conversation Dialog Area (Dashed lines, Avatars, Timestamps)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0),
                child: ListView.builder(
                  controller: _scrollController,
                  physics: const BouncingScrollPhysics(),
                  itemCount: _segments.length,
                  itemBuilder: (context, index) {
                    final segment = _segments[index];
                    final bool isLast = index == _segments.length - 1;

                    return IntrinsicHeight(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Left column (Avatar, Timestamp, Vertical Dash-line)
                          Column(
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  color: segment.color,
                                  shape: BoxShape.circle,
                                ),
                                child: Center(
                                  child: Text(
                                    segment.speakerInitials,
                                    style: const TextStyle(
                                      fontFamily: 'Inter',
                                      fontSize: 15.0,
                                      fontWeight: FontWeight.w700,
                                      color: Colors.white,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                segment.timestamp,
                                style: const TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 11.0,
                                  color: Colors.white38,
                                ),
                              ),
                              if (!isLast)
                                Expanded(
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 8.0),
                                    child: CustomPaint(
                                      size: const Size(1, double.infinity),
                                      painter: DashLinePainter(),
                                    ),
                                  ),
                                )
                              else
                                const SizedBox(height: 20),
                            ],
                          ),
                          const SizedBox(width: 16),

                          // Right column (Speech bubble / text block)
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.only(bottom: 24.0, top: 4.0),
                              child: Text(
                                segment.text,
                                style: const TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 16.0,
                                  height: 1.45,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),

            // 4. Bottom Stop Meeting Button (Slightly smaller & centered)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48.0, vertical: 16.0),
              child: GestureDetector(
                onTap: () {
                  Navigator.pushReplacementNamed(context, '/details', arguments: 'meeting_demo');
                },
                child: Container(
                  height: 52, // Made smaller (52 instead of 64)
                  decoration: BoxDecoration(
                    color: const Color(0xFF1C1215), // Dark red tinted box
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFEF4444).withOpacity(0.15)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 14,
                        height: 14,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEF4444),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      const SizedBox(width: 10),
                      const Text(
                        "Stop Meeting",
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 15.0,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFFEF4444),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildParticipantAvatar(String name, Color color) {
    return Padding(
      padding: const EdgeInsets.only(right: 16.0),
      child: Column(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                name,
                style: const TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 15.0,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(height: 6),
          // Small waveform simulator under each avatar
          Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              return Container(
                width: 2,
                height: (i == 1 ? 10.0 : 6.0),
                margin: const EdgeInsets.symmetric(horizontal: 1),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.8),
                  borderRadius: BorderRadius.circular(1),
                ),
              );
            }),
          )
        ],
      ),
    );
  }

  Widget _buildMoreAvatar(String text) {
    return Padding(
      padding: const EdgeInsets.only(right: 16.0),
      child: Column(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              color: Color(0xFF1E2027),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                text,
                style: const TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 14.0,
                  fontWeight: FontWeight.w600,
                  color: Colors.white54,
                ),
              ),
            ),
          ),
          const SizedBox(height: 6),
          const SizedBox(height: 10), // empty space offset matching waveforms
        ],
      ),
    );
  }
}

// Custom Painter to draw clean dashed lines between message nodes
class DashLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    const double dashHeight = 4.0;
    const double dashSpace = 4.0;
    double startY = 0;

    while (startY < size.height) {
      canvas.drawLine(
        Offset(size.width / 2, startY),
        Offset(size.width / 2, startY + dashHeight),
        paint,
      );
      startY += dashHeight + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
