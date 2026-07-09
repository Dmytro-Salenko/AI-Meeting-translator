class ApiConfig {
  // Публичный домен бэкенда для E2E-тестов
  static const String domain = "ai-meeting-backend-vd28.onrender.com";
  
  static const String apiBaseUrl = "https://$domain/api/v1";
  static const String wsBaseUrl = "wss://$domain/api/v1";

  /// Возвращает полный URL для WebSocket соединения по meetingId
  static String meetingWsUrl(String meetingId) {
    return "$wsBaseUrl/ws/meeting/$meetingId";
  }
}
