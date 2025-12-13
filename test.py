import sys

import time
import pickle

import whisperx
import torch

print(f"torch.version.cuda={torch.version.cuda}")
print(f"torch.backends.cudnn.version={torch.backends.cudnn.version()}")

import dotenv

import os
from typing import Optional, Union
from pyannote.audio import Pipeline
from whisperx.diarize import DiarizationPipeline
from whisperx.log_utils import get_logger

logger = get_logger(__name__)


dotenv.load_dotenv("~/.env")
dotenv.load_dotenv(".env")
start_time = time.time()

device = os.getenv("device", "cpu")  # "cpu" # "cuda"
batch_size = 16  # reduce if low on GPU mem
compute_type = os.getenv("compute_type",
                         "int8")  # "int8" # "float16" # change to "int8" if low on GPU mem (may reduce accuracy)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 1. Transcribe with original whisper (batched)
logger.info("Loading model")
model = whisperx.load_model(os.getenv("whisperx_model_name", "large-v2"), device,
                            compute_type=compute_type,
                            download_root=os.getenv("whisperx_download_root", "./models"))
file_name = "./media_452785_msg_452785.oga"
file_name = "./audio.wav"
# class LocalDiarizationPipeline(DiarizationPipeline):
#     """
#     DiarizationPipeline с гарантированной загрузкой модели из локального диска
#     (через HuggingFace cache).
#     """
#
#     def __init__(
#         self,
#         model_name: str = "pyannote/speaker-diarization-3.1",
#         device: Optional[Union[str, torch.device]] = "cpu",
#         cache_dir: Optional[str] = None,
#         use_auth_token: Optional[str] = None,
#         offline: bool = True,
#     ):
#         if isinstance(device, str):
#             device = torch.device(device)
#
#         # Жёстко включаем оффлайн-режим (по желанию)
#         if offline:
#             os.environ.setdefault("HF_HUB_OFFLINE", "1")
#             os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
#
#         print(
#             f"Loading diarization model (local): {model_name}, cache_dir={cache_dir}"
#         )
#
#         # ПЕРЕОПРЕДЕЛЯЕМ self.model вместо вызова super().__init__()
#         self.model = Pipeline.from_pretrained(
#             model_name,
#             cache_dir=cache_dir,
#             use_auth_token=use_auth_token,
#         ).to(device)


class LocalDiarizationPipeline(DiarizationPipeline):
    def __init__(
        self,
            model_name = None,
        device="cpu",
        cache_dir="./models",
            offline: bool = False,
    ):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        logger.info("Loading diarization pipeline (offline, local cache)")

        self.model = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            cache_dir=cache_dir,
            #use_auth_token=True,  # берёт HF_TOKEN
        ).to(torch.device(device))


print("Loading diarize_model")
# diarize_model = LocalDiarizationPipeline(
#     model_name= os.getenv("diarize_model_name","pyannote/speaker-diarization-3.1"),
#     device=device,  # cuda или "cpu"
#     cache_dir=os.getenv("whisperx_download_root", "./models"),
#     offline=True,
# )
#
# with open('./models/diarize_model.pkl', 'wb') as file:
#     pickle.dump(diarize_model, file)

with open('./models/diarize_model.pkl', 'rb') as file:
    diarize_model = pickle.load(file)

transcribasiotn_start_time = time.time()
try:
    logger.info(f"Loading audio '{file_name}'")
    audio = whisperx.load_audio(file_name)
    result = model.transcribe(audio, batch_size=batch_size)
except Exception as e:
    print(e)
    raise e
logger.info(result["segments"])  # before alignment

# delete model if low on GPU resources
# import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model

# 2. Align whisper output
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

print(result["segments"])  # after alignment

print(f" Took time: {time.time() - start_time} seconds")
print(f" transcribastion Took time: {time.time() - transcribasiotn_start_time} seconds")
# delete model if low on GPU resources
# import gc
# import torch
# gc.collect()
# torch.cuda.empty_cache()
# del model_a
# #
# # 3. Assign speaker labels
assign_word_speakers_start = time.time()

# add min/max number of speakers if known
diarize_segments = diarize_model(audio, min_speakers=2,
                                 max_speakers=2)
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

for s in result.get("segments"):
    #print(s)

    print(f"'{s.get('start')}-{s.get('end')}' : {s.get('speaker')} : {s.get('text')} ")