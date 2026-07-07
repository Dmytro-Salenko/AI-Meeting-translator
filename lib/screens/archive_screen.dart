import 'package:flutter/material.dart';

class ArchiveScreen extends StatefulWidget {
  const ArchiveScreen({Key? key}) : super(key: key);

  @override
  State<ArchiveScreen> createState() => _ArchiveScreenState();
}

class _ArchiveScreenState extends State<ArchiveScreen> {
  final TextEditingController _searchController = TextEditingController();
  
  // Dummy archive list
  final List<Map<String, dynamic>> _meetings = [
    {
      "id": "meeting_demo_1",
      "title": "Встреча: Архитектура Поиска",
      "date": "2026-07-07",
      "duration": "00:15",
    },
    {
      "id": "meeting_demo_2",
      "title": "Синхронизация по R2 Бакетам",
      "date": "2026-07-06",
      "duration": "00:22",
    }
  ];

  List<Map<String, dynamic>> _searchResults = [];
  bool _isSearching = false;
  String? _aiSummaryAnswer;

  void _runSearch(String query) async {
    if (query.trim().isEmpty) {
      setState(() {
        _searchResults = [];
        _aiSummaryAnswer = null;
        _isSearching = false;
      });
      return;
    }

    setState(() {
      _isSearching = true;
    });

    // Emulate semantic API response from: GET /meetings/search?q=query
    await Future.delayed(const Duration(milliseconds: 800));

    setState(() {
      _isSearching = false;
      _aiSummaryAnswer = "На встрече 2026-07-07 Спикер A (Dmitry) рассказал об архитектуре поиска [0:06].";
      _searchResults = [
        {
          "meeting_id": "meeting_demo_1",
          "meeting_title": "Встреча: Архитектура Поиска",
          "speaker_name": "Speaker A (Dmitry)",
          "start_time": 6.0,
          "text": "Это позволит пользователям писать вопросы на русском, украинском и английском языках.",
        }
      ];
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0E12),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          "Архив встреч",
          style: TextStyle(fontFamily: 'Inter', fontSize: 18.0, fontWeight: FontWeight.w600),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0),
        child: Column(
          children: [
            // AI Search Bar
            TextField(
              controller: _searchController,
              style: const TextStyle(color: Colors.white),
              onSubmitted: _runSearch,
              decoration: InputDecoration(
                hintText: "Спросите ИИ о встречах...",
                hintStyle: const TextStyle(color: Colors.white38),
                prefixIcon: const Icon(Icons.psychology_outlined, color: Colors.blueAccent),
                filled: true,
                fillColor: const Color(0xFF16171D),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16.0),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Search Results or Meetings List
            Expanded(
              child: _isSearching
                  ? const Center(child: CircularProgressIndicator(color: Colors.blueAccent))
                  : _searchController.text.isNotEmpty
                      ? _buildSearchResults()
                      : _buildMeetingsList(),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildSearchResults() {
    return ListView(
      physics: const BouncingScrollPhysics(),
      children: [
        if (_aiSummaryAnswer != null) ...[
          const Text(
            "Ответ ИИ-Агента",
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blueAccent, fontSize: 14),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              color: const Color(0xFF16171D),
              borderRadius: BorderRadius.circular(16.0),
              border: Border.all(color: Colors.blueAccent.withOpacity(0.2)),
            ),
            child: Text(
              _aiSummaryAnswer!,
              style: const TextStyle(color: Colors.white, height: 1.45),
            ),
          ),
          const SizedBox(height: 24),
        ],
        const Text(
          "Найденные сегменты",
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white54, fontSize: 14),
        ),
        const SizedBox(height: 8),
        ..._searchResults.map((res) {
          return Card(
            color: const Color(0xFF16171D),
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: ListTile(
              onTap: () {
                Navigator.pushNamed(context, '/details', arguments: res["meeting_id"]);
              },
              title: Text(res["meeting_title"], style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text(
                "${res['speaker_name']} [${res['start_time']}s]:\n${res['text']}",
                style: const TextStyle(color: Colors.white70),
              ),
              trailing: const Icon(Icons.play_arrow, color: Colors.blueAccent),
            ),
          );
        }).toList()
      ],
    );
  }

  Widget _buildMeetingsList() {
    return ListView.builder(
      physics: const BouncingScrollPhysics(),
      itemCount: _meetings.length,
      itemBuilder: (context, index) {
        final meeting = _meetings[index];
        return Card(
          color: const Color(0xFF16171D),
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: ListTile(
            onTap: () {
              Navigator.pushNamed(context, '/details', arguments: meeting["id"]);
            },
            title: Text(meeting["title"]!, style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text("Дата: ${meeting['date']!} | Длительность: ${meeting['duration']!}"),
            trailing: const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.white30),
          ),
        );
      },
    );
  }
}
