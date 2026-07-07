import modal
import os

# 1. Создаем образ серверной среды для видеокарты
# Устанавливаем системные аудио-библиотеки (ffmpeg) и нужные нейросети
app_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg")
    .pip_install(
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
    
    print("💾 Запись результатов в базу данных Supabase...")
    # Шаг E. Построчно сохраняем сегменты в таблицу `meeting_segments`
    for segment in final_result["segments"]:
        start_time = segment["start"]
        end_time = segment["end"]
        text = segment["text"]
        speaker_label = segment.get("speaker", "Speaker X")
        
        # Логика интеграции с домашней базой профилей участников
        # Сначала проверяем, есть ли уже этот спикер в таблице `profiles`
        profile_res = supabase.table("profiles").select("id").eq("voice_fingerprint", speaker_label).execute()
        
        if profile_res.data:
            speaker_id = profile_res.data[0]["id"]
        else:
            # Создаем новый профиль для нового голоса, если его еще не было
            new_profile = supabase.table("profiles").insert({
                "name": f"Новый спикер ({speaker_label})",
                "voice_fingerprint": speaker_label
            }).execute()
            speaker_id = new_profile.data[0]["id"]
            
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
