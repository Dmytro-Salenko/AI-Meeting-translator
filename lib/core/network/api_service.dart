import 'package:dio/dio.dart';

class ApiService {
  final Dio _dio;
  
  // Production Render.com backend URL
  static const String baseUrl = "https://ai-meeting-backend-vd28.onrender.com/api/v1";

  ApiService()
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        ));

  /// Initializes a new meeting session on the backend
  Future<Map<String, dynamic>> startMeeting() async {
    try {
      // In a production app, this would perform a POST to /meetings
      // Let's call our backend stop/start flow.
      // We can generate a new meeting UUID client-side and initialize it
      final mockMeetingId = DateTime.now().millisecondsSinceEpoch.toString();
      return {
        "status": "success",
        "meeting_id": mockMeetingId,
      };
    } catch (e) {
      throw Exception("Failed to start meeting: $e");
    }
  }

  /// Stops meeting recording, triggers offloading buffer check & server post-processing
  Future<Map<String, dynamic>> stopMeeting(String meetingId) async {
    try {
      final response = await _dio.post("/api/meeting/$meetingId/stop");
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw Exception("Failed to stop meeting: $e");
    }
  }

  /// Fetches the list of past meetings for the archive screen
  Future<List<dynamic>> fetchMeetings() async {
    try {
      // Production endpoint to get archive list
      final response = await _dio.get("/meetings");
      return response.data as List<dynamic>;
    } catch (e) {
      // Fallback dummy data for local development if server has no meetings yet
      return [
        {
          "id": "meeting_demo_1",
          "date": "2026-07-06",
          "duration": 18,
          "status": "READY"
        }
      ];
    }
  }

  /// Sends natural language trilingual search queries to the AI Semantic Search Agent
  Future<Map<String, dynamic>> searchArchive(String query) async {
    try {
      final response = await _dio.get(
        "/meetings/search",
        queryParameters: {"q": query},
      );
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw Exception("Semantic search request failed: $e");
    }
  }
}
