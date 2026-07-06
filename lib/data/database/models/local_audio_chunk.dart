enum UploadStatus {
  pending,
  uploaded,
}

class LocalAudioChunk {
  final String id;
  final String meetingId;
  final int chunkIndex;
  final DateTime timestampStart;
  final DateTime timestampEnd;
  final String filePath;
  final String checksum;
  final UploadStatus uploadStatus;

  LocalAudioChunk({
    required this.id,
    required this.meetingId,
    required this.chunkIndex,
    required this.timestampStart,
    required this.timestampEnd,
    required this.filePath,
    required this.checksum,
    required this.uploadStatus,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'meetingId': meetingId,
      'chunkIndex': chunkIndex,
      'timestampStart': timestampStart.toIso8601String(),
      'timestampEnd': timestampEnd.toIso8601String(),
      'filePath': filePath,
      'checksum': checksum,
      'uploadStatus': uploadStatus.name,
    };
  }

  factory LocalAudioChunk.fromMap(Map<String, dynamic> map) {
    return LocalAudioChunk(
      id: map['id'] as String,
      meetingId: map['meetingId'] as String,
      chunkIndex: map['chunkIndex'] as int,
      timestampStart: DateTime.parse(map['timestampStart'] as String),
      timestampEnd: DateTime.parse(map['timestampEnd'] as String),
      filePath: map['filePath'] as String,
      checksum: map['checksum'] as String,
      uploadStatus: UploadStatus.values.byName(map['uploadStatus'] as String),
    );
  }

  LocalAudioChunk copyWith({
    String? id,
    String? meetingId,
    int? chunkIndex,
    DateTime? timestampStart,
    DateTime? timestampEnd,
    String? filePath,
    String? checksum,
    UploadStatus? uploadStatus,
  }) {
    return LocalAudioChunk(
      id: id ?? this.id,
      meetingId: meetingId ?? this.meetingId,
      chunkIndex: chunkIndex ?? this.chunkIndex,
      timestampStart: timestampStart ?? this.timestampStart,
      timestampEnd: timestampEnd ?? this.timestampEnd,
      filePath: filePath ?? this.filePath,
      checksum: checksum ?? this.checksum,
      uploadStatus: uploadStatus ?? this.uploadStatus,
    );
  }
}
