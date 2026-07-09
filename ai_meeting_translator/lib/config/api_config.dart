class ApiConfig {
  // Введите IP-адрес вашего компьютера в локальной сети для связи с запущенным FastAPI
  static const String host = "192.168.1.100"; 
  
  static const String baseUrl = "http://$host:8000/api/v1";
  static const String wsUrl = "ws://$host:8000/api/v1/ws/meeting";
}
