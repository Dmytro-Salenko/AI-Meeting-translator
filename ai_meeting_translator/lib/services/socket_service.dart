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
    final wsUrlString = ApiConfig.meetingWsUrl(meetingId);
    final uri = Uri.parse(wsUrlString);

    try {
      print("WebSocket URL: $wsUrlString");
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      onConnectionStatusChanged?.call(true);
      print("WebSocket connected");

      // Listen for translation responses from the server
      _channel!.stream.listen(
        (message) {
          print("Backend message received: $message");
          if (message is String) {
            _translationController.add(message);
          }
        },
        onError: (error) {
          print("WebSocket error: $error");
          _handleDisconnect();
        },
        onDone: () {
          print("WebSocket closed");
          _handleDisconnect();
        },
      );
    } catch (e) {
      print("WebSocket connection failed: $e");
      _handleDisconnect();
    }
  }

  /// Handles clean reconnection on network drops
  void _handleDisconnect() {
    print("Backend disconnected");
    _isConnected = false;
    onConnectionStatusChanged?.call(false);
    _channel = null;

    // Retry connection if we are still supposed to be actively recording
    if (_isRecording) {
      print("Attempting to reconnect in 3 seconds...");
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
      print("Requesting microphone permission...");
      if (await _recorder.hasPermission()) {
        print("microphone permission granted");
        _isRecording = true;
        print("recording started");

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
              print("Chunk sent. Size: ${chunk.length} bytes");
              _channel!.sink.add(Uint8List.fromList(chunk));
            } else {
              print("Chunk not sent. Connected: $_isConnected, Channel: ${_channel != null}");
            }
          },
          onError: (err) {
            print("Recording stream error: $err");
            stopRecordingAndStreaming();
          },
        );
      } else {
        print("Microphone permission denied");
      }
    } catch (e) {
      print("Failed to start recording: $e");
      stopRecordingAndStreaming();
    }
  }

  /// Stops audio streaming and closes the WebSocket connection cleanly
  Future<void> stopRecordingAndStreaming() async {
    print("Recording stopped");
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
