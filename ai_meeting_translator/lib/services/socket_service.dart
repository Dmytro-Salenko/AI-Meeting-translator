import 'dart:async';
import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:record/record.dart';
import '../config/api_config.dart';

class SocketService {
  WebSocketChannel? _channel;
  final AudioRecorder _recorder = AudioRecorder();
  StreamSubscription<List<int>>? _recordSubscription;
  
  bool _isConnected = false;
  bool _isRecording = false;
  String _currentMeetingId = "";
  
  // Stream controller to broadcast received translations to UI
  final StreamController<String> _translationController = StreamController<String>.broadcast();
  Stream<String> get translationStream => _translationController.stream;

  // Callback to inform UI of connection status changes
  void Function(bool isConnected)? onConnectionStatusChanged;

  /// Connects to the WebSocket endpoint with reconnection logic
  Future<void> connect(String meetingId) async {
    _currentMeetingId = meetingId;
    final uri = Uri.parse("${ApiConfig.wsUrl}?meeting_id=$meetingId");

    try {
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      onConnectionStatusChanged?.call(true);

      // Listen for translation responses from the server
      _channel!.stream.listen(
        (message) {
          if (message is String) {
            _translationController.add(message);
          }
        },
        onError: (error) {
          _handleDisconnect();
        },
        onDone: () {
          _handleDisconnect();
        },
      );
    } catch (e) {
      _handleDisconnect();
    }
  }

  /// Handles clean reconnection on network drops
  void _handleDisconnect() {
    _isConnected = false;
    onConnectionStatusChanged?.call(false);
    _channel = null;

    // Retry connection if we are still supposed to be actively recording
    if (_isRecording) {
      Future.delayed(const Duration(seconds: 3), () {
        if (_isRecording && !_isConnected) {
          connect(_currentMeetingId);
        }
      });
    }
  }

  /// Starts streaming raw PCM audio chunks from microphone to WebSocket
  Future<void> startRecordingAndStreaming() async {
    if (_isRecording) return;

    try {
      // Request microphone permissions
      if (await _recorder.hasPermission()) {
        _isRecording = true;

        // Configure streaming with raw PCM audio at 16kHz, 16bit, mono (ideal for Whisper/STT)
        final recordConfig = const RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: 16000,
          numChannels: 1,
        );

        final audioStream = await _recorder.startStream(recordConfig);
        
        _recordSubscription = audioStream.listen(
          (chunk) {
            if (_isConnected && _channel != null) {
              // Send binary PCM chunk over WebSocket
              _channel!.sink.add(Uint8List.fromList(chunk));
            }
          },
          onError: (err) {
            stopRecordingAndStreaming();
          },
        );
      }
    } catch (e) {
      stopRecordingAndStreaming();
    }
  }

  /// Stops audio streaming and closes the WebSocket connection cleanly
  Future<void> stopRecordingAndStreaming() async {
    _isRecording = false;
    _isConnected = false;
    
    await _recordSubscription?.cancel();
    _recordSubscription = null;
    
    await _recorder.stop();
    await _channel?.sink.close();
    _channel = null;
    
    onConnectionStatusChanged?.call(false);
  }

  void dispose() {
    stopRecordingAndStreaming();
    _translationController.close();
  }
}
