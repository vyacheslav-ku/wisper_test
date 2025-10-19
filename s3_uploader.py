import boto3
from botocore.client import Config
import os
import dotenv

dotenv.load_dotenv(".env")
def upload_directory_to_s3(local_dir, bucket_name, s3_prefix=""):
    """
    Загружает все файлы из local_dir в S3 bucket (включая поддиректории).
    :param local_dir: локальная директория для загрузки
    :param bucket_name: имя S3 бакета
    :param s3_prefix: префикс (папка) в бакете
    """
    # Создание клиента S3
    s3_client = boto3.client(
        "s3",
        endpoint_url=os.getenv("minio_endpoint"),
        aws_access_key_id=os.getenv("minio_access_key"),
        aws_secret_access_key=os.getenv("minio_secret_key"),
        config=Config(signature_version="s3v4")
    )

    # Рекурсивный обход всех файлов в директории
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            # Относительный путь файла внутри local_dir
            relative_path = os.path.relpath(local_path, local_dir)
            # Путь в бакете
            s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")

            try:
                s3_client.upload_file(local_path, bucket_name, s3_key)
                print(f"✅ Загружен: {local_path} → s3://{bucket_name}/{s3_key}")
            except Exception as e:
                print(f"❌ Ошибка при загрузке {local_path}: {e}")

if __name__ == "__main__":
    # Пример использования:
    local_directory = os.getenv("upload_dir", "/models")   # директория для загрузки
    bucket_name = os.getenv("minio_bucket_name", "mybucket")
    s3_prefix = os.getenv("s3_prefix", "")  # например, "backups/" или ""

    upload_directory_to_s3(local_directory, bucket_name, s3_prefix)
