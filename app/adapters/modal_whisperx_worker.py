import modal

# Define the container image with necessary OS packages, CUDA, PyTorch and WhisperX
whisperx_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "git", "wget")
    .pip_install(
        "torch==2.1.2",
        "torchaudio==2.1.2",
        "index-override",
        extra_options="--index-url https://download.pytorch.org/whl/cu118"
    )
    .pip_install(
        "git+https://github.com/m-bain/whisperX.git",
        "boto3",
        "soundfile"
    )
    # Pre-download and cache model during container build step to avoid cold start lag
    .run_commands(
        "python -c 'import whisperx; whisperx.load_model(\"medium\", \"cuda\", compute_type=\"float16\")'"
    )
)

app = modal.App("whisperx-app", image=whisperx_image)


@app.function(
    gpu="A10G",
    timeout=600,
    secrets=[
        modal.Secret.from_name("huggingface-secret"), # For HF_TOKEN
        modal.Secret.from_name("cloudflare-r2-secret") # For R2 AWS credentials
    ]
)
def process_audio(meeting_id: str, r2_file_path: str) -> list[dict]:
    """
    Downloads full assembled audio from Cloudflare R2, executes WhisperX transcription,
    word alignment, and speaker diarization, then returns parsed speaker segments.
    """
    import os
    import boto3
    import whisperx
    import torch

    device = "cuda"
    batch_size = 16
    compute_type = "float16"

    # 1. Download audio file from R2 to local container scratch disk
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        endpoint_url=os.environ["R2_ENDPOINT_URL"]
    )
    
    local_audio_path = f"/tmp/{meeting_id}_final.wav"
    s3.download_file(
        Bucket=os.environ["R2_BUCKET_NAME"],
        Key=r2_file_path,
        Filename=local_audio_path
    )

    # 2. Transcribe audio with WhisperX
    model = whisperx.load_model("medium", device, compute_type=compute_type)
    audio = whisperx.load_audio(local_audio_path)
    result = model.transcribe(audio, batch_size=batch_size)
    
    # Clean up model to release GPU memory before alignment/diarization
    del model
    torch.cuda.empty_cache()

    # 3. Align Whisper output timestamps
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], 
        device=device
    )
    aligned_result = whisperx.align(
        result["segments"], 
        model_a, 
        metadata, 
        audio, 
        device, 
        return_char_alignments=False
    )
    
    del model_a
    torch.cuda.empty_cache()

    # 4. Perform Speaker Diarization using PyAnnote (requires HF_TOKEN)
    hf_token = os.environ.get("HF_TOKEN")
    diarize_model = whisperx.DiarizationPipeline(
        use_auth_token=hf_token, 
        device=device
    )
    
    diarize_segments = diarize_model(
        audio, 
        min_speakers=1, 
        max_speakers=10
    )
    
    # 5. Assign speakers to aligned text segments
    final_segments = whisperx.assign_word_speakers(diarize_segments, aligned_result)

    # 6. Format segments into standard payload structure
    output = []
    for seg in final_segments["segments"]:
        output.append({
            "start_time": float(seg.get("start", 0.0)),
            "end_time": float(seg.get("end", 0.0)),
            "speaker_id": str(seg.get("speaker", "Speaker Unknown")),
            "original_text": str(seg.get("text", "")).strip()
        })

    # Cleanup temp file
    if os.path.exists(local_audio_path):
        os.remove(local_audio_path)

    return output
