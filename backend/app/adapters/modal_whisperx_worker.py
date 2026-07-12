import modal
import os

# 1. Создаем образ серверной среды для видеокарты
# Устанавливаем системные аудио-библиотеки (ffmpeg) и нужные нейросети
app_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg")
    .pip_install(
        "numpy==1.26.4",
        "transformers==4.39.3",
        "whisperx==3.1.1",
        "supabase==2.3.0",
        "boto3==1.34.0",
        "torch==2.1.2",
        "torchaudio==2.1.2"
    )
)

# Регистрируем наше облачное ИИ-приложение в системе Modal
app = modal.App(name="ai-meeting-processor", image=app_image)

# 2. Главная функция обработки митинга, работающая НА ВИДЕОКАРТЕ (GPU)
# Подключаем наш созданный сейф с ключами через .secrets
@app.function(
    gpu="T4",  # Оптимальная по цене/скорости бесплатная видеокарта NVIDIA
    secrets=[modal.Secret.from_name("ai-meeting-secrets")],
    timeout=1200  # Защита от зависания: максимум 20 минут на митинг
)
def process_meeting_async(meeting_id: str):
    import boto3
    from supabase import create_client, Client
    import whisperx
    import torch
    
    print(f"🚀 ИИ-Воркер запущен. Начинаем обработку встречи: {meeting_id}")
    
    # Подключаемся к Supabase и Cloudflare R2 внутри видеокарты
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
    
    r2_bucket = os.environ["R2_BUCKET_NAME"]
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"]
    )
    
    # Шаг A. Скачиваем аудиофайл встречи из Cloudflare R2 во временную память видеокарты
    local_audio_path = f"/tmp/{meeting_id}.mp3"
    object_key = f"meetings/{meeting_id}/final_audio.mp3"
    
    print("📥 Скачиваем аудиозапись из Cloudflare R2...")
    s3_client.download_file(r2_bucket, object_key, local_audio_path)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" # Ускоренное вычисление для видеокарт
    
    # Шаг B. Запускаем высокоточное распознавание текста (STT Faster-Whisper)
    print("🎙️ Нейросеть распознает речь (STT)...")
    model = whisperx.load_model("large-v2", device, compute_type=compute_type, language="en")
    audio = whisperx.load_audio(local_audio_path)
    result = model.transcribe(audio, batch_size=16)
    
    # Шаг C. Выравнивание таймингов слов (чтобы перевод бежал ровно секунда в секунду)
    model_a, metadata = whisperx.load_align_model(language_code="en", device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    # Шаг D. Диаризация: Разделение голосов (Кто именно говорит: Спикер А, Спикер Б)
    print("👥 Разделяем голоса спикеров на аудиозаписи (Diarization)...")
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
    diarize_segments = diarize_model(audio)
    
    # Объединяем текст и разделенные голоса вместе
    final_result = whisperx.assign_word_speakers(diarize_segments, result)
    
    print("👥 Вычисляем embeddings для спикеров...")
    # Инициализируем модель speaker embedding
    from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
    import numpy as np
    
    embedding_model = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb", device=device)
    
    # 1. Группируем сегменты по локальным меткам SPEAKER_XX
    speaker_segments = {}
    for segment in final_result["segments"]:
        label = segment.get("speaker")
        if label:
            if label not in speaker_segments:
                speaker_segments[label] = []
            speaker_segments[label].append(segment)
            
    # 2. Вычисляем centroid для каждого спикера
    # Порог 0.75 выбран как стартовый ориентир для косинусного сходства векторов модели ECAPA-TDNN (требует калибровки)
    SIMILARITY_THRESHOLD = 0.75
    
    # Загружаем всех существующих спикеров из базы
    try:
        existing_speakers_res = supabase.table("speakers").select("user_assigned_name", "voiceprint_metadata").execute()
        existing_speakers = existing_speakers_res.data or []
    except Exception as e:
        print(f"Ошибка чтения существующих спикеров из БД: {e}")
        existing_speakers = []
        
    speaker_mappings = {} # Локальный лейбл -> {"profile_id": ..., "name": ...}
    
    for label, segments in speaker_segments.items():
        # Выбираем от 3 до 5 самых длинных аудиосегментов
        sorted_segs = sorted(segments, key=lambda s: s["end"] - s["start"], reverse=True)
        target_segs = sorted_segs[:5]
        
        embeddings = []
        for seg in target_segs:
            start_sample = int(seg["start"] * 16000)
            end_sample = int(seg["end"] * 16000)
            seg_audio = audio[start_sample:end_sample]
            
            # Проверяем, что сегмент достаточно длинный (не менее 0.1 секунды)
            if len(seg_audio) >= 1600:
                seg_tensor = torch.from_numpy(seg_audio).unsqueeze(0).unsqueeze(0).to(device) # shape (1, 1, samples)
                with torch.no_grad():
                    try:
                        emb = embedding_model(seg_tensor)
                    except Exception:
                        emb = embedding_model(seg_tensor.squeeze(1))
                    embeddings.append(emb.cpu().numpy().flatten())
                    
        if not embeddings:
            print(f"Спикер {label}: Нет подходящих аудиофрагментов для извлечения эмбеддингов")
            continue
            
        print(f"Спикер {label}: embedding created. Число сегментов: {len(embeddings)}")
        
        # Усредняем эмбеддинги в centroid и нормализуем его
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / np.linalg.norm(centroid)
        
        # Сравниваем с ранее сохраненными спикерами
        best_similarity = -1.0
        best_match = None
        
        for spk in existing_speakers:
            metadata = spk.get("voiceprint_metadata")
            if metadata and isinstance(metadata, dict) and "embedding" in metadata:
                saved_emb = np.array(metadata["embedding"])
                # Косинусное сходство нормализованных векторов - это скалярное произведение
                sim = float(np.dot(centroid, saved_emb))
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = spk
                    
        print(f"Спикер {label}: Best similarity score: {best_similarity:.4f}")
        
        # Принимаем решение о сопоставлении
        if best_similarity >= SIMILARITY_THRESHOLD and best_match:
            matched_profile_id = best_match["voiceprint_metadata"]["profile_id"]
            matched_name = best_match["user_assigned_name"]
            print(f"Спикер {label}: matched existing speaker '{matched_name}' (ID: {matched_profile_id})")
            
            # Создаем новую запись в speakers для привязки к текущему митингу
            supabase.table("speakers").insert({
                "meeting_id": meeting_id,
                "user_assigned_name": matched_name,
                "voiceprint_metadata": {
                    "embedding": centroid.tolist(),
                    "model": "speechbrain/spkrec-ecapa-voxceleb",
                    "dimension": 192,
                    "profile_id": matched_profile_id
                }
            }).execute()
            
            speaker_mappings[label] = {
                "profile_id": matched_profile_id,
                "name": matched_name
            }
        else:
            print(f"Спикер {label}: совпадений не найдено. Создаем нового спикера.")
            # Регистрируем новый глобальный профиль
            # Для обеспечения уникальности voice_fingerprint используем строку встречи и лейбла
            unique_fingerprint = f"{meeting_id}_{label}"
            new_name = f"Новый спикер ({label})"
            
            new_profile_res = supabase.table("profiles").insert({
                "name": new_name,
                "voice_fingerprint": unique_fingerprint
            }).execute()
            
            profile_id = new_profile_res.data[0]["id"]
            
            # Регистрируем спикера во встрече
            supabase.table("speakers").insert({
                "meeting_id": meeting_id,
                "user_assigned_name": new_name,
                "voiceprint_metadata": {
                    "embedding": centroid.tolist(),
                    "model": "speechbrain/spkrec-ecapa-voxceleb",
                    "dimension": 192,
                    "profile_id": profile_id
                }
            }).execute()
            
            speaker_mappings[label] = {
                "profile_id": profile_id,
                "name": new_name
            }

    print("💾 Запись результатов в базу данных Supabase...")
    # Шаг E. Построчно сохраняем сегменты в таблицу `meeting_segments`
    for segment in final_result["segments"]:
        start_time = segment["start"]
        end_time = segment["end"]
        text = segment["text"]
        speaker_label = segment.get("speaker", "Speaker X")
        
        # Получаем привязанный на предыдущем шаге глобальный profile_id
        mapping = speaker_mappings.get(speaker_label)
        if mapping:
            speaker_id = mapping["profile_id"]
        else:
            # Fallback на случай отсутствия эмбеддинга (например, слишком короткая реплика)
            speaker_id = None
            
        # Отправляем готовую строчку текста встречи в базу данных
        supabase.table("meeting_segments").insert({
            "meeting_id": meeting_id,
            "speaker_id": speaker_id,
            "speaker_label": speaker_label,
            "start_time": start_time,
            "end_time": end_time,
            "original_text": text,
            "russian_translation": "" # Поле для будущего перевода
        }).execute()
        
    # Обновляем статус встречи в базе — теперь она готова для генерации саммари через OpenRouter
    supabase.table("meetings").update({"status": "PROCESSING"}).eq("id", meeting_id).execute()
    
    # Удаляем временный аудиофайл с видеокарты ради полной конфиденциальности
    if os.path.exists(local_audio_path):
        os.remove(local_audio_path)
        
    print(f"🎉 Обработка встречи {meeting_id} успешно завершена!")
    return {"status": "success"}


@app.cls(
    gpu="T4",
    timeout=60
)
class LiveTranscriber:
    @modal.enter()
    def load_model(self):
        from faster_whisper import WhisperModel
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if torch.cuda.is_available() else "float32"
        print("Modal model loaded: Initializing 'base' faster-whisper model...")
        self.model = WhisperModel("base", device=device, compute_type=compute_type)

    @modal.method()
    def transcribe(self, audio_data: bytes) -> str:
        """
        Fast remote GPU method to transcribe a short 3-second audio WAV buffer
        using the base Whisper model cached in container memory.
        """
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Transcribe audio file using faster-whisper
            segments, info = self.model.transcribe(tmp_path)
            
            # Extract text
            text = " ".join([seg.text for seg in segments]).strip()
            
            print(f"Modal transcription completed: '{text}'")
            return text
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
