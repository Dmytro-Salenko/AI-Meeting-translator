import 'package:equatable/equatable';

enum MeetingStatus {
  created,
  recording,
  networkLost,
  recordingBuffering,
  uploadFinalizing,
  processing,
  ready,
  failed,
}

abstract class MeetingState extends Equatable {
  final MeetingStatus status;
  final String meetingId;
  final String translationText;
  final List<String> pendingQueue;
  final String errorMessage;

  const MeetingState({
    required this.status,
    required this.meetingId,
    this.translationText = '',
    this.pendingQueue = const [],
    this.errorMessage = '',
  });

  @override
  List<Object?> get props => [status, meetingId, translationText, pendingQueue, errorMessage];
}

class MeetingInitial extends MeetingState {
  const MeetingInitial({required String meetingId})
      : super(status: MeetingStatus.created, meetingId: meetingId);
}

class MeetingRecording extends MeetingState {
  const MeetingRecording({
    required String meetingId,
    required String translationText,
  }) : super(
          status: MeetingStatus.recording,
          meetingId: meetingId,
          translationText: translationText,
        );
}

class MeetingNetworkLost extends MeetingState {
  const MeetingNetworkLost({
    required String meetingId,
    required String translationText,
    required List<String> pendingQueue,
  }) : super(
          status: MeetingStatus.networkLost,
          meetingId: meetingId,
          translationText: translationText,
          pendingQueue: pendingQueue,
        );
}

class MeetingBuffering extends MeetingState {
  const MeetingBuffering({
    required String meetingId,
    required String translationText,
    required List<String> pendingQueue,
  }) : super(
          status: MeetingStatus.recordingBuffering,
          meetingId: meetingId,
          translationText: translationText,
          pendingQueue: pendingQueue,
        );
}

class MeetingFinalizing extends MeetingState {
  const MeetingFinalizing({
    required String meetingId,
    required List<String> pendingQueue,
  }) : super(
          status: MeetingStatus.uploadFinalizing,
          meetingId: meetingId,
          pendingQueue: pendingQueue,
        );
}

class MeetingProcessing extends MeetingState {
  const MeetingProcessing({required String meetingId})
      : super(status: MeetingStatus.processing, meetingId: meetingId);
}

class MeetingReady extends MeetingState {
  const MeetingReady({required String meetingId})
      : super(status: MeetingStatus.ready, meetingId: meetingId);
}

class MeetingFailure extends MeetingState {
  const MeetingFailure({
    required String meetingId,
    required String errorMessage,
  }) : super(
          status: MeetingStatus.failed,
          meetingId: meetingId,
          errorMessage: errorMessage,
        );
}
