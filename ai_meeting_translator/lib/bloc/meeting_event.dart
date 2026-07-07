import 'dart:typed_data';
import 'package:equatable/equatable.dart';

abstract class MeetingEvent extends Equatable {
  const MeetingEvent();

  @override
  List<Object?> get props => [];
}

class StartMeeting extends MeetingEvent {
  final String meetingId;
  const StartMeeting(this.meetingId);

  @override
  List<Object?> get props => [meetingId];
}

class AudioChunkAvailable extends MeetingEvent {
  final Uint8List chunkData;
  const AudioChunkAvailable(this.chunkData);

  @override
  List<Object?> get props => [chunkData];
}

class NetworkStatusChanged extends MeetingEvent {
  final bool isConnected;
  const NetworkStatusChanged(this.isConnected);

  @override
  List<Object?> get props => [isConnected];
}

class LiveTranslationReceived extends MeetingEvent {
  final String translation;
  const LiveTranslationReceived(this.translation);

  @override
  List<Object?> get props => [translation];
}

class StopMeeting extends MeetingEvent {
  const StopMeeting();
}

class SyncCompleted extends MeetingEvent {
  const SyncCompleted();
}

class ServerProcessingComplete extends MeetingEvent {
  const ServerProcessingComplete();
}

class MeetingFailedEvent extends MeetingEvent {
  final String error;
  const MeetingFailedEvent(this.error);

  @override
  List<Object?> get props => [error];
}
