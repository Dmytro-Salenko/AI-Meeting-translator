# BACKEND INTEGRATION INVENTORY
**Проект: AI Meeting Translator (FastAPI Backend)**

Этот документ представляет собой полную инвентаризацию сетевых интеграций, зависимостей, моделей данных, потоков (pipelines) и настроек окружения для FastAPI-бэкенда. Разработан для ИИ-инженеров и системных архитекторов с целью передачи контекста разработки.

---

## 1. ВНЕШНИЕ СЕРВИСЫ И ИХ ИНТЕГРАЦИЯ

Бэкенд интегрирован со следующими внешними облачными системами и провайдерами:

### 1. Supabase (База Данных)
*   **Где используется**: Инициализируется и вызывается внутри удаленного GPU-обработчика Modal (`backend/app/adapters/modal_whisperx_worker.py`), а также логически подготавливается в фоновых задачах (`backend/app/tasks/meeting_tasks.py`).
*   **Файлы и Классы**:
    *   `backend/app/adapters/modal_whisperx_worker.py` (функции `process_audio` и `whisperx_worker_pipeline`).
*   **Используемые ENV-переменные**:
    *   `SUPABASE_URL` (ссылка на API проект)
    *   `SUPABASE_SERVICE_ROLE_KEY` (приватный админ-ключ для обхода ограничений RLS)
*   **Эндпоинты**:
    *   `https://<supabase-id>.supabase.co`
*   **Запросы**:
    *   `SELECT id FROM profiles WHERE voice_fingerprint = ...`
    *   `INSERT INTO profiles (id, voice_fingerprint, name) VALUES (...)`
    *   `INSERT INTO meeting_segments (meeting_id, speaker_id, start_time, end_time, original_text) VALUES (...)`
    *   `UPDATE meetings SET status = 'PROCESSING' WHERE id = ...`
*   **Статус реализации**: *Реализовано на стороне удаленного GPU-воркера*. На стороне основного FastAPI-сервиса вызовы к Supabase в фоновых задачах `process_full_meeting_async` сейчас заменены на **Mocks** (комментарии и запись в локальный `MOCK_DB` словарь).

### 2. Cloudflare R2 / S3 Storage (Файловое хранилище)
*   **Где используется**: Используется для загрузки аудио-чанков и сборки результирующего Wav-файла встречи.
*   **Файлы и Классы**:
    *   `backend/app/adapters/s3_storage.py` $\rightarrow$ класс `S3StorageProvider`.
    *   `backend/app/adapters/modal_whisperx_worker.py` (загрузка аудиофайла на GPU-воркере).
*   **Используемые ENV-переменные**:
    *   `R2_BUCKET_NAME`
    *   `R2_ENDPOINT_URL`
    *   `R2_ACCESS_KEY_ID`
    *   `R2_SECRET_ACCESS_KEY`
*   **Запросы**:
    *   Вызовы API Amazon S3 (через библиотеку `boto3`). Выполняется метод `put_object` для сохранения бинарных RAW-данных аудио-кусков и итогового собранного файла встречи.
*   **Статус реализации**: *Реализовано* (класс `S3StorageProvider` готов, но его включение зависит от значения `STORAGE_PROVIDER="r2"` в `.env`). По умолчанию используется заглушка `MockStorageProvider`, которая пишет данные в локальный словарь `MOCK_DB`.

### 3. OpenRouter (Генерация AI-Summary)
*   **Где используется**: Используется для анализа полной текстовой стенограммы завершенного митинга и выделения резюме и задач.
*   **Файлы и Классы**:
    *   `backend/app/adapters/openrouter_summary.py` $\rightarrow$ класс `OpenRouterSummaryProvider`.
*   **Используемые ENV-переменные**:
    *   `OPENROUTER_API_KEY` (приватный ключ)
    *   `OPENROUTER_MODEL` (идентификатор ИИ модели, например `deepseek/deepseek-chat`)
*   **Эндпоинты**:
    *   `https://openrouter.ai/api/v1/chat/completions` (HTTP POST)
*   **Формат Request**:
    ```json
    {
      "model": "deepseek/deepseek-chat",
      "messages": [{"role": "user", "content": "..."}]
    }
    ```
*   **Формат Response**:
    Стандартный JSON-формат ответов OpenAI Chat Completions.
*   **Статус реализации**: *Реализовано* (класс `OpenRouterSummaryProvider` полностью готов к интеграции и отправке HTTP-запросов через `httpx`).

### 4. DeepL (Переводчик)
*   **Где используется**: Используется для перевода расшифрованных Whisper-сегментов с оригинального языка на русский.
*   **Файлы и Классы**:
    *   `backend/app/adapters/deepl_translation.py` $\rightarrow$ класс `DeepLTranslationProvider`.
*   **Используемые ENV-переменные**:
    *   `DEEPL_API_KEY`
*   **Эндпоинты**:
    *   `https://api-free.deepl.com/v2/translate` или `https://api.deepl.com/v2/translate` (зависит от структуры ключа).
*   **Статус реализации**: *Реализовано* (класс `DeepLTranslationProvider` готов, отправляет запросы через клиент `httpx`).

### 5. Modal / WhisperX / Hugging Face (Постобработка и диаризация)
*   **Где используется**: Запуск удаленной транскрибации с разделением спикеров.
*   **Файлы и Классы**:
    *   `backend/app/adapters/modal_worker.py` $\rightarrow$ класс `ModalGPUWorkerAdapter`.
    *   `backend/app/adapters/modal_whisperx_worker.py` (удаленный код воркера).
*   **Используемые ENV-переменные**:
    *   `MODAL_WORKER_URL`
    *   `HF_TOKEN` (для pyannote)
*   **Статус реализации**: *Частично*. Код воркера для Modal.com написан, клиентский адаптер `ModalGPUWorkerAdapter` вызывает удаленную функцию `process_audio`. Однако в `meeting_tasks.py` вызов воркера заблокирован заглушкой.

---

## 2. АНАЛИЗ ЧТЕНИЯ ENV-ПЕРЕМЕННЫХ И ИСПОЛЬЗУЕМЫХ КЛИЕНТОВ

### Вызовы os.getenv(...) / os.environ:
1.  `backend/main.py`:
    *   `os.getenv("ENVIRONMENT", "production")` — определение среды запуска.
    *   `os.getenv("PORT", 8000)` — биндинг веб-порта uvicorn.
2.  `backend/app/routers/meeting_stream.py`:
    *   `os.getenv("USE_MOCK_STT", "false")` — включение отладочного STT транспорта во Flutter.
3.  `backend/app/adapters/modal_whisperx_worker.py`:
    *   `os.environ["SUPABASE_URL"]`
    *   `os.environ["SUPABASE_SERVICE_ROLE_KEY"]`
    *   `os.environ["R2_BUCKET_NAME"]`
    *   `os.environ["R2_ENDPOINT_URL"]`
    *   `os.environ["R2_ACCESS_KEY_ID"]`
    *   `os.environ["R2_SECRET_ACCESS_KEY"]`

### Обращения к settings.* (Pydantic BaseSettings):
Все настройки из класса `Settings` (`backend/app/core/config.py`) считываются через импортируемый объект `settings`:
*   `settings.DATABASE_URL`, `settings.SUPABASE_URL`, `settings.SUPABASE_KEY`
*   `settings.STORAGE_PROVIDER`, `settings.TRANSLATION_PROVIDER`, `settings.SUMMARY_PROVIDER`
*   `settings.R2_BUCKET_NAME`, `settings.R2_ACCOUNT_ID`, `settings.R2_ACCESS_KEY_ID`, `settings.R2_SECRET_ACCESS_KEY`, `settings.R2_ENDPOINT_URL`
*   `settings.DEEPL_API_KEY`, `settings.OPENROUTER_API_KEY`, `settings.OPENROUTER_MODEL`

### Используемые HTTP / SDK Клиенты:
1.  **httpx** (AsyncClient) — используется во всех адаптерах (`deepl_translation.py`, `openrouter_summary.py`, `meeting_stream.py`).
2.  **supabase-py** (`create_client`) — используется воркером Modal для записи стенограмм в PostgreSQL.
3.  **boto3** (S3 client) — используется для связи с Cloudflare R2 в `s3_storage.py`.
4.  **modal** (modal.Function) — используется для триггера GPU-задач.

---

## 3. СЕТЕВЫЕ ИНТЕГРАЦИИ (REST / WEBSOCKET)

### Входящие WebSocket Endpoints:
*   `WS /api/v1/ws/meeting/{meeting_id}`
    *   *Назначение*: Прием звука в реальном времени и стриминг сегментов перевода.
    *   *Входящий формат*: Бинарные PCM-пакеты (audio chunks).
    *   *Исходящий формат*:
        ```json
        {
          "type": "segment",
          "speaker": "Speaker 1",
          "text": "Hello...",
          "translation": "Привет...",
          "timestamp": "HH:MM:SS"
        }
        ```

### REST API Endpoints бэкенда:
1.  `POST /api/v1/meetings/start`
    *   *Инициализация встречи*. Возвращает UUID встречи.
2.  `POST /api/v1/meetings/{meeting_id}/stop`
    *   *Остановка сессии*. Триггерит запуск асинхронной постобработки собранного аудиофайла.
3.  `POST /api/v1/meetings/upload`
    *   *Загрузка готовой карточки встречи* (метаданные, саммари, стенограмма) от мобильного клиента.
4.  `GET /api/v1/meetings`
    *   *Список архивных встреч*. Возвращает массив метаданных.
5.  `GET /api/v1/meetings/search`
    *   *Семантический ИИ-поиск по архиву*. Параметр запроса: `q` (текстовый запрос).

---

## 4. МОДЕЛИ ДАННЫХ И ХРАНЕНИЕ

### Модели данных:
1.  **Meeting (Встреча)**: Свойства: `id`, `status` (CREATED, RECORDING, NETWORK_LOST, FAILED, PROCESSING, READY), `chunks` (словарь чанков), `summary` (ИИ резюме), `segments` (массив реплик).
2.  **Segment (Реплика)**: Свойства: `speaker_id`, `start_time`, `end_time`, `original_text`, `russian_translation`.

### Локации хранения данных:
*   **Бэкенд Mocks (MOCK_DB)**: Глобальный in-memory словарь `MOCK_DB = {}` в `meeting_stream.py`. Хранит все сессии, активные чанки и стенограммы в оперативной памяти бэкенда. При перезапуске сервера все данные стираются.
*   **Supabase (Реальное хранилище)**: Таблицы `meetings`, `meeting_segments`, `profiles`. Используются только кодом воркера Modal при постобработке.

---

## 5. ХАРАКТЕРИСТИКА ТАБЛИЦ И СХЕМ

### Таблица ENV-переменных:

| Variable | Required/Optional | Service | Used in file | Purpose | Secret? | Status in .env.example | Needed for E2E test? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Required | Supabase DB | `config.py` | Подключение к PostgreSQL | **Yes** | Placeholder | **No** (используется mock DB) |
| `SUPABASE_URL` | Optional | Supabase | `config.py`, `modal_whisperx_worker.py` | URL API Supabase | No | Placeholder | **No** |
| `SUPABASE_KEY` | Optional | Supabase | `config.py` | Публичный анон-ключ Supabase | No | Placeholder | **No** |
| `SUPABASE_SERVICE_ROLE_KEY` | Required | Supabase | `modal_whisperx_worker.py` | Сервисный токен администратора | **Yes** | **Missing** | **No** |
| `STORAGE_PROVIDER` | Required | R2/Local | `config.py`, `dependencies.py` | Выбор файлового провайдера | No | `"r2"` | **No** (fallback на Mock) |
| `R2_BUCKET_NAME` | Optional | Cloudflare R2 | `config.py`, `modal_whisperx_worker.py` | Имя бакета для аудио | No | `"meeting-audio-chunks"` | **No** |
| `R2_ACCESS_KEY_ID` | Optional | Cloudflare R2 | `config.py`, `modal_whisperx_worker.py` | S3 Access Key | **Yes** | Placeholder | **No** |
| `R2_SECRET_ACCESS_KEY` | Optional | Cloudflare R2 | `config.py`, `modal_whisperx_worker.py` | S3 Secret Key | **Yes** | Placeholder | **No** |
| `DEEPL_API_KEY` | Optional | DeepL | `config.py`, `dependencies.py` | Ключ перевода DeepL | **Yes** | Placeholder | **No** |
| `OPENROUTER_API_KEY` | Optional | OpenRouter | `config.py`, `dependencies.py` | Ключ ИИ саммаризации | **Yes** | Placeholder | **No** |
| `USE_MOCK_STT` | Optional | System Mock | `meeting_stream.py` | Отладка фронта без ИИ | No | **Missing** | **Yes** (для симуляции перевода) |

---

### Таблица Внешних API вызовов (External API Calls):

| Service | Method | URL | Auth | Used in File | Request Format | Response Format | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DeepL** | `POST` | `/v2/translate` | Bearer Token | `deepl_translation.py` | URL-Encoded Form | JSON array | Ready |
| **OpenRouter** | `POST` | `/chat/completions` | Bearer Token | `openrouter_summary.py` | JSON payload | JSON OpenAI-like | Ready |
| **Modal GPU** | `POST` | `/process_audio` | Client Lookup | `modal_worker.py` | Remote method args | JSON array | Ready |

---

## 6. GAP ANALYSIS (АНАЛИЗ РАСХОЖДЕНИЙ АРХИТЕКТУРЫ)

| Feature | Expected Architecture | Current Implementation | Status | Next Required Action |
| :--- | :--- | :--- | :--- | :--- |
| **Live STT** | Аудио чанк $\rightarrow$ Модель $\rightarrow$ Текст | PCM накопление $\rightarrow$ RealSTT placeholder (пустой лог) | **Mock / Missing** | Подключить Groq/OpenAI Whisper API в `RealSTTProvider` |
| **Diarization** | Разделение спикеров на GPU | Celery вызывает `process_full_meeting_async`, но функция `whisper_x_diarization_mock` **не объявлена в коде** | **Bug / Missing** | Объявить/импортировать `whisper_x_diarization_mock` или интегрировать `ModalGPUWorkerAdapter` |
| **База Данных** | Сохранение встреч в Supabase | Данные о сессиях живут в оперативной памяти `MOCK_DB` бэкенда | **Mock** | Переписать `dependencies.py` и роутеры на чтение/запись в Supabase Client |

---

## 7. МИНИМАЛЬНЫЕ СЛЕДУЮЩИЕ ШАГИ (MINIMUM NEXT STEPS)

Чтобы запустить **реальное** распознавание голоса (Speech-To-Text) на бэкенде, выполните:

1.  **Создайте реальный STT-провайдер** (например, через Groq Cloud API):
    *   Создайте файл `backend/app/adapters/groq_stt.py` с классом `GroqSTTProvider`, отправляющим накопленные WAV-байты на `https://api.groq.com/openai/v1/audio/transcriptions`.
2.  **Добавьте ENV-переменные в настройки хостинга**:
    *   `GROQ_API_KEY` (секретный токен из личного кабинета Groq).
3.  **Переключите провайдер в `get_stt_provider()`**:
    *   Замените в `meeting_stream.py` класс `RealSTTProvider` на вызов `GroqSTTProvider(api_key=os.getenv("GROQ_API_KEY"))`.
4.  **Устраните критический баг NameError в фоновых тасках**:
    *   Импортируйте `ModalGPUWorkerAdapter` в `meeting_tasks.py` и перепишите строку:
        `segments = await modal_worker.trigger_diarization(meeting_id, final_path)`
        вместо неиствующей функции `whisper_x_diarization_mock`.
