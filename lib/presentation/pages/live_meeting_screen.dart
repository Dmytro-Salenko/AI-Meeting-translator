import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../bloc/meeting_bloc.dart';
import '../bloc/meeting_event.dart';
import '../bloc/meeting_state.dart';

class LiveMeetingScreen extends StatefulWidget {
  const LiveMeetingScreen({Key? key}) : super(key: key);

  @override
  State<LiveMeetingScreen> createState() => _LiveMeetingScreenState();
}

class _LiveMeetingScreenState extends State<LiveMeetingScreen> {
  final ScrollController _scrollController = ScrollController();

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12),
      body: SafeArea(
        child: BlocConsumer<MeetingBloc, MeetingState>(
          listener: (context, state) {
            if (state is MeetingRecording || state is MeetingBuffering || state is MeetingNetworkLost) {
              WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
            }
            if (state is MeetingProcessing) {
              Navigator.pushReplacementNamed(context, '/processing');
            }
          },
          builder: (context, state) {
            return Column(
              children: [
                // 1. Reactive Network Status Bar
                _buildStatusBar(state),
                
                // 2. Fade Gradient Masked Live Translation Text Area
                Expanded(
                  child: ShaderMask(
                    shaderCallback: (Rect bounds) {
                      return const LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          Color(0xFF0D0E12),
                        ],
                        stops: [0.0, 0.15],
                      ).createShader(bounds);
                    },
                    blendMode: BlendMode.dstIn,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                      child: ListView.builder(
                        controller: _scrollController,
                        physics: const BouncingScrollPhysics(),
                        itemCount: 1,
                        itemBuilder: (context, index) {
                          return Text(
                            state.translationText.isEmpty 
                                ? "Ожидание речи..." 
                                : state.translationText,
                            style: const TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 22.0,
                              height: 1.65,
                              fontWeight: FontWeight.w400,
                              color: Colors.white,
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                ),

                // 3. Floating Control Capsule Panel (Stop Action)
                Padding(
                  padding: const EdgeInsets.only(bottom: 32.0, top: 16.0),
                  child: _buildStopButton(context),
                )
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildStatusBar(MeetingState state) {
    Color badgeColor;
    String statusText;

    switch (state.status) {
      case MeetingStatus.recording:
        badgeColor = const Color(0xFF10B981); // Emerald Green
        statusText = "🟢 ЗАПИСЬ ИДЕТ";
        break;
      case MeetingStatus.networkLost:
        badgeColor = const Color(0xFFF59E0B); // Amber Yellow
        statusText = "🟡 СВЯЗЬ ПОТЕРЯНА • Кэширование";
        break;
      case MeetingStatus.recordingBuffering:
        badgeColor = const Color(0xFF3B82F6); // Blue
        statusText = "🔵 ВОССТАНОВЛЕНИЕ • Синк буфера";
        break;
      case MeetingStatus.uploadFinalizing:
        badgeColor = Colors.grey;
        statusText = "⚪ СИНХРОНИЗАЦИЯ БУФЕРА";
        break;
      default:
        badgeColor = Colors.grey;
        statusText = "ПОДКЛЮЧЕНИЕ...";
    }

    return Container(
      margin: const EdgeInsets.all(16.0),
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
      decoration: BoxDecoration(
        color: const Color(0xFF16171D),
        borderRadius: BorderRadius.circular(16.0),
        boxShadow: [
          BoxShadow(
            color: badgeColor.withOpacity(0.05),
            blurRadius: 10,
            spreadRadius: 2,
          )
        ]
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: badgeColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            statusText,
            style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 14.0,
              fontWeight: FontWeight.w600,
              color: badgeColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStopButton(BuildContext context) {
    return GestureDetector(
      onTap: () {
        context.read<MeetingBloc>().add(const StopMeeting());
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 48.0, vertical: 16.0),
        decoration: BoxDecoration(
          color: const Color(0xFF8B0000), // Dark Red Capsule
          borderRadius: BorderRadius.circular(30.0),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF8B0000).withOpacity(0.3),
              blurRadius: 15,
              offset: const Offset(0, 4),
            )
          ]
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [
            Icon(Icons.stop, color: Colors.white, size: 24),
            SizedBox(width: 8),
            Text(
              "STOP",
              style: TextStyle(
                fontFamily: 'Inter',
                fontSize: 16.0,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
