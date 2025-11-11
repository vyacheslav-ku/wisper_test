from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import hashlib
import os
from typing import Optional
import time
import os
import json
import whisperx
# import torch
# torch.backends.cuda.matmul.allow_tf32 = False
# torch.backends.cudnn.allow_tf32 = False
import torch

print(f"torch.version.cuda={torch.version.cuda}")
print(f"torch.backends.cudnn.version={torch.backends.cudnn.version()}")

import gc
from whisperx.diarize import DiarizationPipeline
import dotenv

dotenv.load_dotenv("~/.env")
dotenv.load_dotenv(".env")
start_time = time.time()
print(os.environ)
print("=========")
device = os.getenv("device", "cuda")  # "cpu" # "cuda"
batch_size = 16  # reduce if low on GPU mem
compute_type = os.getenv("compute_type",
                         "float16")  # "int8" # "float16" # change to "int8" if low on GPU mem (may reduce accuracy)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. Transcribe with original whisper (batched)
model = whisperx.load_model(os.getenv("whisperx_model_name", "large-v2"), device,
                            compute_type=compute_type,
                            download_root=os.getenv("whisperx_download_root", "./models"))
app = FastAPI()




def process_audio(file_name: str = None, min_speakers: int = 1, max_speakers: int = 1) -> dict:
    transcribasiotn_start_time = time.time()
    audio = whisperx.load_audio(file_name)
    result = model.transcribe(audio, batch_size=batch_size)
    print(result["segments"])  # before alignment

    # delete model if low on GPU resources
    # import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model

    # 2. Align whisper output
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    print(result["segments"])  # after alignment

    print(f" Took time: {time.time() - start_time} seconds")
    print(f" transcribastion Took time: {time.time() - transcribasiotn_start_time} seconds")
    # delete model if low on GPU resources
    import gc
    import torch
    gc.collect()
    torch.cuda.empty_cache()
    del model_a
    #
    # # 3. Assign speaker labels
    assign_word_speakers_start = time.time()
    diarize_model = DiarizationPipeline(os.getenv("diarization_model_name", 'pyannote/speaker-diarization-3.1'),
                                        use_auth_token=os.getenv("use_auth_token"),
                                        device=device)

    # add min/max number of speakers if known
    diarize_segments = diarize_model(audio, min_speakers=min_speakers,
                                     max_speakers=max_speakers)
    # diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

    result = whisperx.assign_word_speakers(diarize_segments, result)
    print("diarize_segments")
    print(diarize_segments)
    print("result")
    print(result["segments"])  # segments are now assigned speaker IDs
    result['processed_time'] = time.time() - start_time
    print(f"transcribasiotn_start_time time: {time.time() - transcribasiotn_start_time} seconds")
    print(f"Total time: {time.time() - start_time} seconds")
    print(f"assign_word_speakers_start time: {time.time() - assign_word_speakers_start} seconds")
    return result


# curl -X POST "http://127.0.0.1:8000/upload/"  -F "file=@audio.wav"  -F "description=Test file" -F "author=Vyacheslav"
@app.post("/upload/")
async def upload_file(
        file: UploadFile = File(...),
        response_type: Optional[str] = Form("json"),
        count_of_speakers_min: Optional[int] = Form(1),
        count_of_speakers_max: Optional[int] = Form(1),
):
    """
    Загружает файл с метаданными (описание, автор) и сохраняет его локально.
    Возвращает размер файла и SHA256-хеш.
    """
    if count_of_speakers_min > count_of_speakers_max:
        count_of_speakers_max = count_of_speakers_min

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Сохраняем файл
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Вычисляем размер и хеш
    file_size = os.path.getsize(file_path)
    file_hash = hashlib.sha256(content).hexdigest()
    result = process_audio(file_name=file_path, min_speakers=count_of_speakers_min,
                           max_speakers=count_of_speakers_max)

    result.update({
        "filename": file.filename,
        "size_bytes": file_size,
        "sha256": file_hash,
        "meta": {
            "response_type": response_type,

        }}
    )
    if response_type == "json":
        return result
    elif response_type == "text":
        if count_of_speakers_max == 1:
            text_list = []
            for s in result.get("segments"):
                # print(s)

                text_list.append(f"{s.get('text')}")
            return {'data': "\n".join(text_list)}
        text_list = []
        for s in result.get("segments"):
            # print(s)

            text_list.append(f"'{s.get('start')}-{s.get('end')}' : {s.get('speaker')} : {s.get('text')} ")
        return {'data': "\n".join(text_list),
                'regments' : result.get("segments")
                }
