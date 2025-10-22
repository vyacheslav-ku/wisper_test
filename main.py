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
#print(os.environ)
print("=========")
device = os.getenv("device", "cuda") #"cpu" # "cuda"
audio_file = os.getenv("audio_file", "audio.wav")
batch_size = 16 # reduce if low on GPU mem
compute_type = os.getenv("compute_type", "float16") #"int8" # "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

# 1. Transcribe with original whisper (batched)
model = whisperx.load_model(os.getenv("whisperx_model_name","large-v2"), device,
                            compute_type=compute_type,
                            download_root=os.getenv("whisperx_download_root","./models"))

# save model to local path (optional)
# model_dir = "/path/"
# model = whisperx.load_model("large-v2", device, compute_type=compute_type, download_root=model_dir)
transcribasiotn_start_time = time.time()
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)
print(result["segments"]) # before alignment

# delete model if low on GPU resources
# import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model

# 2. Align whisper output
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

print(result["segments"]) # after alignment

print(f" Took time: {time.time() - start_time} seconds")
print(f" transcribastion Took time: {time.time() - transcribasiotn_start_time} seconds")
# delete model if low on GPU resources
import gc; import torch; gc.collect(); torch.cuda.empty_cache(); del model_a
#
# # 3. Assign speaker labels
diarize_model = DiarizationPipeline(os.getenv("diarization_model_name",'pyannote/speaker-diarization-3.1'),
                                    use_auth_token=os.getenv("use_auth_token"),
                                    device=device)

# add min/max number of speakers if known
diarize_segments = diarize_model(audio)
# diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

result = whisperx.assign_word_speakers(diarize_segments, result)
print("diarize_segments")
print(diarize_segments)
print("result")
print(result["segments"]) # segments are now assigned speaker IDs
result['processed_time'] = time.time() - start_time
with open(os.path.join(os.getenv("base_directory","./"), f"{audio_file}_diarized.json"), "w") as f:
    json.dump(result, f)