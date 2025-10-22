FROM python:3.10.13-slim-bullseye
RUN apt-get update && apt-get install -y ffmpeg  && rm -fr /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir boto3 dotenv whisperx