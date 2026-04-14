from datetime import timedelta
from pathlib import Path
import os
from typing import Union

from minio import Minio
from minio.error import S3Error

class MinIOClient:
    def __init__(
            self, 
            endpoint: str = "", 
            access_key: str = "", 
            secret_key: str = "",
            secure: bool = False,
            region: str = None):

        self.client = Minio(
            endpoint or os.getenv("S3_ENDPOINT", "localhost:9000"),
            access_key=access_key or os.getenv("S3_ACCESS_KEY"),
            secret_key=secret_key or os.getenv("S3_SECRET_KEY"),
            secure=secure,
            region=region
            )
        
    def create_bucket(self, bucket_name: str, location: str = None):
        try:
            if location:
                self.client.make_bucket(bucket_name, location=location)
            else:
                self.client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created successfully.")
        except S3Error as e:
            if e.code != 'BucketAlreadyOwnedByYou':
                print(f"Bucket '{bucket_name}' already exists and is owned by you.")
            elif e.code != 'BucketAlreadyExists':
                print(f"Bucket '{bucket_name}' already exists and is owned by someone else.")
            else:
                print(f"Error creating bucket: {e}")

    def bucket_exists(self, bucket_name: str) -> bool:
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            print(f"Error checking bucket existence: {e}")
            return False

    def upload_file(self, bucket_name: str, object_name: str, file_path: Path):
        try:
            self.client.fput_object(bucket_name, object_name, str(file_path))
            print(f"File '{file_path}' uploaded to bucket '{bucket_name}' as '{object_name}'.")
        except S3Error as e:
            print(f"Error uploading file: {e}")

    def download_file(self, bucket_name: str, object_name: str, file_path: Path):
        try:
            self.client.fget_object(bucket_name, object_name, str(file_path))
            print(f"File '{object_name}' downloaded from bucket '{bucket_name}' to '{file_path}'.")
        except S3Error as e:
            print(f"Error downloading file: {e}")

    def list_objects(self, bucket_name: str):
        try:
            objects = self.client.list_objects(bucket_name)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"Error listing objects: {e}")
            return []

    def delete_object(self, bucket_name: str, object_name: str):
        try:
            self.client.remove_object(bucket_name, object_name)
            print(f"Object '{object_name}' deleted from bucket '{bucket_name}'.")
        except S3Error as e:
            print(f"Error deleting object: {e}")

    def generate_presigned_url(self, bucket_name: str, object_name: str, expiration: Union[int, float, timedelta] = 60):
        # Convert default expiration from minutes to timedelta
        if isinstance(expiration, (int, float)):
            expiration = timedelta(minutes=expiration)
        try:
            url = self.client.presigned_get_object(bucket_name, object_name, expires=expiration)
            print(f"Presigned URL for '{object_name}': {url}")
            return url
        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            return ""
        
if __name__ == "__main__":
    # Example usage
    minio_client = MinIOClient(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )