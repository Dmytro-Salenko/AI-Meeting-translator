import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import '../models/local_audio_chunk.dart';

abstract class MeetingSyncDelegate {
  void onTranslationReceived(String text);
  void onNetworkStatusChanged(bool isConnected);
  void onSyncFinished();
  void onSyncError(String error);
}

class MeetingSyncService {
  final String serverUrl = "http://10.0.2.2:8000"; // standard Android emulator host IP
  final String wsUrl = "ws://10.0.2.2:8000";
  
  MeetingSyncDelegate? delegate;
  bool _isConnected = true;
  Timer? _heartbeatTimer;
  Timer? _syncTimer;
  int _chunkCounter = 0;
  
  // In-memory cache representing SQLite/Hive Local Database
  final List<LocalAudioChunk> _localDb = [];
  bool _isSyncing = false;

  void setDelegate(MeetingSyncDelegate delegate) {
    this.delegate = delegate;
  }

  // Generate MD5 checksum of bytes
  String _calculateMd5(Uint8List bytes) {
    return md5.convert(bytes).toString();
  }

  // --------------------------------------------------------------------------
  // NETWORK SIMULATOR & WEBSOCKET OPERATIONS
  // --------------------------------------------------------------------------

  Future<void> connect(String meetingId) async {
    _chunkCounter = 0;
    _startHeartbeat();
    _startBackgroundSyncWorker(meetingId);
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 10), (timer) {
      if (_isConnected) {
        // Send ping control signal to WebSocket
        // In real app: webSocket.sink.add(jsonEncode({'type': 'ping'}));
      }
    });
  }

  void disconnect() {
    _heartbeatTimer?.cancel();
    _syncTimer?.cancel();
  }

  // --------------------------------------------------------------------------
  // AUDIO WRITER & LOCAL CACHE (RELIABILITY CONTOUR)
  // --------------------------------------------------------------------------

  Future<void> handleAudioChunk(String meetingId, Uint8List chunkBytes) async {
    final int index = _chunkCounter++;
    final DateTime now = DateTime.now();
    final DateTime start = now.subtract(const Duration(milliseconds: 500));
    final String md5Hash = _calculateMd5(chunkBytes);
    final String mockPath = "/data/user/0/com.example/meeting_$meetingId/chunk_$index.wav";

    // Save to Local DB (Contour of reliability)
    final newChunk = LocalAudioChunk(
      id: "chunk_${meetingId}_$index",
      meetingId: meetingId,
      chunkIndex: index,
      timestampStart: start,
      timestampEnd: now,
      filePath: mockPath,
      checksum: md5Hash,
      uploadStatus: UploadStatus.pending,
    );
    
    _localDb.add(newChunk);

    if (_isConnected) {
      // Stream raw audio to server via WebSocket
      // In real app: webSocket.sink.add(chunkBytes);
      
      // Simulate live translation return callback
      final mockResponseWord = _getMockTranslationWord(index);
      delegate?.onTranslationReceived(mockResponseWord);
      
      // Mark chunk as uploaded
      _markChunkUploaded(newChunk.id);
    } else {
      // Cache locally and notify state machine of offline mode
      delegate?.onNetworkStatusChanged(false);
    }
  }

  void _markChunkUploaded(String chunkId) {
    final idx = _localDb.indexWhere((c) => c.id == chunkId);
    if (idx != -1) {
      _localDb[idx] = _localDb[idx].copyWith(uploadStatus: UploadStatus.uploaded);
    }
  }

  // Simulates HTTP Multipart POST API upload of pending chunks
  Future<void> _startBackgroundSyncWorker(String meetingId) async {
    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(const Duration(milliseconds: 1500), (timer) async {
      if (!_isConnected || _isSyncing) return;

      final pendingChunks = _localDb
          .where((c) => c.meetingId == meetingId && c.uploadStatus == UploadStatus.pending)
          .toList();

      if (pendingChunks.isEmpty) return;

      _isSyncing = true;
      
      // Sync chunks one by one (HTTP Multipart emulation)
      for (final chunk in pendingChunks) {
        await Future.delayed(const Duration(milliseconds: 200)); // Network delay
        
        // Emulate Server Upload POST request response:
        // httpx POST to /api/meeting/{id}/upload-chunk
        _markChunkUploaded(chunk.id);
      }

      _isSyncing = false;

      // Check if queue is completely drained
      final remaining = _localDb.any((c) => c.meetingId == meetingId && c.uploadStatus == UploadStatus.pending);
      if (!remaining) {
        delegate?.onSyncFinished();
      }
    });
  }

  // --------------------------------------------------------------------------
  // COLD START RECOVERY
  // --------------------------------------------------------------------------
  Future<void> runColdStartRecovery() async {
    // Queries local DB for outstanding chunks across all meetings
    final pending = _localDb.where((c) => c.uploadStatus == UploadStatus.pending).toList();
    if (pending.isNotEmpty) {
      for (final chunk in pending) {
        await Future.delayed(const Duration(milliseconds: 100)); // HTTP POST request
        _markChunkUploaded(chunk.id);
      }
    }
  }

  // Helper toggle to simulate network drops in demo mode
  void toggleNetworkConnection(bool connected) {
    _isConnected = connected;
    delegate?.onNetworkStatusChanged(connected);
  }

  String _getMockTranslationWord(int index) {
    const words = [
      "Привет", "всем,", "спасибо", "что", "присоединились", "к", "нашей", "встрече.",
      "Сегодня", "мы", "должны", "выбрать", "хранилище.",
      "Я", "предлагаю", "использовать", "Cloudflare", "R2", "из-за", "дешевизны", "трафика."
    ];
    return words[min(index, words.length - 1)];
  }
}
