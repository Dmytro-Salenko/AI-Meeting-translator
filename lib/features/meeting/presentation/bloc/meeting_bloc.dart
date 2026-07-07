import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../data/network/meeting_sync_service.dart';
import 'meeting_event.dart';
import 'meeting_state.dart';

class MeetingBloc extends Bloc<MeetingEvent, MeetingState> implements MeetingSyncDelegate {
  final MeetingSyncService _syncService;
  StreamSubscription? _audioRecordingMockSubscription;

  MeetingBloc({required MeetingSyncService syncService})
      : _syncService = syncService,
        super(const MeetingInitial(meetingId: '')) {
    _syncService.setDelegate(this);

    // Event registration
    on<StartMeeting>(_onStartMeeting);
    on<AudioChunkAvailable>(_onAudioChunkAvailable);
    on<NetworkStatusChanged>(_onNetworkStatusChangedEvent);
    on<LiveTranslationReceived>(_onLiveTranslationReceived);
    on<StopMeeting>(_onStopMeeting);
    on<SyncCompleted>(_onSyncCompleted);
    on<ServerProcessingComplete>(_onServerProcessingComplete);
    on<MeetingFailedEvent>(_onMeetingFailed);
  }

  // --------------------------------------------------------------------------
  // EVENT HANDLERS & STATE MACHINE TRANSITIONS
  // --------------------------------------------------------------------------

  Future<void> _onStartMeeting(StartMeeting event, Emitter<MeetingState> emit) async {
    // Only allow start from initial/reset states
    if (state is MeetingInitial || state is MeetingFailure || state is MeetingReady) {
      emit(MeetingRecording(meetingId: event.meetingId, translationText: ''));
      await _syncService.connect(event.meetingId);
      
      // Simulate physical microphone audio stream (Mock Generator)
      _audioRecordingMockSubscription?.cancel();
      _audioRecordingMockSubscription = Stream.periodic(
        const Duration(milliseconds: 500),
        (count) => List<int>.generate(2000, (i) => i % 256), // 2KB mock audio data
      ).listen((bytes) {
        add(AudioChunkAvailable(bytes as dynamic));
      });
    }
  }

  Future<void> _onAudioChunkAvailable(AudioChunkAvailable event, Emitter<MeetingState> emit) async {
    if (state is MeetingRecording || state is MeetingNetworkLost || state is MeetingBuffering) {
      await _syncService.handleAudioChunk(state.meetingId, event.chunkData);
    }
  }

  void _onNetworkStatusChangedEvent(NetworkStatusChanged event, Emitter<MeetingState> emit) {
    final current = state;
    if (event.isConnected) {
      if (current is MeetingNetworkLost) {
        emit(MeetingBuffering(
          meetingId: current.meetingId,
          translationText: current.translationText,
          pendingQueue: current.pendingQueue,
        ));
      }
    } else {
      if (current is MeetingRecording || current is MeetingBuffering) {
        emit(MeetingNetworkLost(
          meetingId: current.meetingId,
          translationText: current.translationText,
          pendingQueue: current.pendingQueue,
        ));
      }
    }
  }

  void _onLiveTranslationReceived(LiveTranslationReceived event, Emitter<MeetingState> emit) {
    final current = state;
    if (current is MeetingRecording || current is MeetingBuffering || current is MeetingNetworkLost) {
      final updatedText = "${current.translationText} ${event.translation}".trim();
      if (current is MeetingRecording) {
        emit(MeetingRecording(meetingId: current.meetingId, translationText: updatedText));
      } else if (current is MeetingBuffering) {
        emit(MeetingBuffering(meetingId: current.meetingId, translationText: updatedText, pendingQueue: current.pendingQueue));
      } else if (current is MeetingNetworkLost) {
        emit(MeetingNetworkLost(meetingId: current.meetingId, translationText: updatedText, pendingQueue: current.pendingQueue));
      }
    }
  }

  Future<void> _onStopMeeting(StopMeeting event, Emitter<MeetingState> emit) async {
    final current = state;
    if (current is MeetingRecording || current is MeetingBuffering || current is MeetingNetworkLost) {
      _audioRecordingMockSubscription?.cancel();
      _syncService.disconnect();

      // Check if there are any remaining offline chunks to upload
      // In real project, checks SQLite table for status = pending
      emit(MeetingFinalizing(meetingId: current.meetingId, pendingQueue: current.pendingQueue));
      
      // If queue is already empty, proceed straight to processing
      if (current.pendingQueue.isEmpty) {
        add(const SyncCompleted());
      }
    }
  }

  void _onSyncCompleted(SyncCompleted event, Emitter<MeetingState> emit) {
    if (state is MeetingFinalizing) {
      emit(MeetingProcessing(meetingId: state.meetingId));
      
      // Simulate server-side long-running background tasks finishing after 4 seconds
      Timer(const Duration(seconds: 4), () {
        add(const ServerProcessingComplete());
      });
    }
  }

  void _onServerProcessingComplete(ServerProcessingComplete event, Emitter<MeetingState> emit) {
    if (state is MeetingProcessing) {
      emit(MeetingReady(meetingId: state.meetingId));
    }
  }

  void _onMeetingFailed(MeetingFailedEvent event, Emitter<MeetingState> emit) {
    _audioRecordingMockSubscription?.cancel();
    _syncService.disconnect();
    emit(MeetingFailure(meetingId: state.meetingId, errorMessage: event.error));
  }

  // --------------------------------------------------------------------------
  // MEETING SYNC DELEGATE CALLBACKS
  // --------------------------------------------------------------------------

  @override
  void onTranslationReceived(String text) {
    add(LiveTranslationReceived(text));
  }

  @override
  void onNetworkStatusChanged(bool isConnected) {
    add(NetworkStatusChanged(isConnected));
  }

  @override
  void onSyncFinished() {
    add(const SyncCompleted());
  }

  @override
  void onError(String error) {
    add(MeetingFailedEvent(error));
  }

  @override
  Future<void> close() {
    _audioRecordingMockSubscription?.cancel();
    _syncService.disconnect();
    return super.close();
  }
}
