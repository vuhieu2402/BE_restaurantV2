"""
Storage Backend Configuration cho MinIO

Convention:
- Tất cả file được lưu vào MinIO bucket
- DB chỉ lưu đường dẫn tới file (relative path từ media/)
- Sử dụng upload_to trong models để định nghĩa path
- Storage class tự động xử lý location và tạo unique filename nếu cần

Ví dụ:
    avatar = ImageField(upload_to='avatars/', storage=MinIOMediaStorage())
    logo = ImageField(upload_to='restaurants/logos/', storage=MinIOMediaStorage())
"""
import json
import logging
import os
import uuid
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class MinIOMediaStorage(S3Boto3Storage):
    """
    Storage class chung cho tất cả media files trong MinIO
    
    Cách sử dụng:
        avatar = ImageField(upload_to='avatars/', storage=MinIOMediaStorage())
        logo = ImageField(upload_to='restaurants/logos/', storage=MinIOMediaStorage())
    
    Tất cả files sẽ được lưu vào: bucket/media/{upload_to}/
    DB chỉ lưu relative path: avatars/filename.jpg
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    file_overwrite = settings.AWS_S3_FILE_OVERWRITE
    default_acl = settings.AWS_DEFAULT_ACL
    location = 'media'  # Base location trong bucket
    
    # Class variable để cache trạng thái bucket đã được kiểm tra
    _bucket_checked = False
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override endpoint URL cho MinIO
        self.endpoint_url = settings.AWS_S3_ENDPOINT_URL

    
    def _ensure_bucket_exists(self):
        """
        Tự động tạo bucket nếu chưa tồn tại
        Chỉ kiểm tra một lần để tránh nhiều requests
        """
        # Kiểm tra cache để tránh gọi nhiều lần
        if MinIOMediaStorage._bucket_checked:
            return
        
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Tạo S3 client với endpoint URL của MinIO
            s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                use_ssl=settings.AWS_S3_USE_SSL,
                verify=settings.AWS_S3_VERIFY,
            )
            
            # Kiểm tra bucket có tồn tại không
            try:
                s3_client.head_bucket(Bucket=self.bucket_name)
                # Đánh dấu đã kiểm tra
                MinIOMediaStorage._bucket_checked = True
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                # MinIO có thể trả về '404' hoặc 'NoSuchBucket'
                if error_code in ('404', 'NoSuchBucket'):
                    # Bucket không tồn tại, tạo mới
                    try:
                        s3_client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Đã tạo bucket '{self.bucket_name}' thành công")
                        
                        # Set public read policy cho bucket
                        try:
                            bucket_policy = {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Principal": {"AWS": "*"},
                                        "Action": ["s3:GetObject"],
                                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                                    }
                                ]
                            }
                            s3_client.put_bucket_policy(
                                Bucket=self.bucket_name,
                                Policy=json.dumps(bucket_policy)
                            )
                            logger.info(f"Đã set public-read policy cho bucket '{self.bucket_name}'")
                        except Exception as policy_error:
                            # Policy có thể không set được, nhưng không block việc tạo bucket
                            logger.warning(f"Không thể set policy cho bucket: {str(policy_error)}")
                        
                        # Đánh dấu đã kiểm tra
                        MinIOMediaStorage._bucket_checked = True
                    except ClientError as create_error:
                        logger.error(f"Không thể tạo bucket '{self.bucket_name}': {str(create_error)}")
                        # Không raise để không block việc khởi động app
                else:
                    # Lỗi khác (403, 500, etc.) - có thể là permission issue
                    logger.warning(f"Lỗi khi kiểm tra bucket '{self.bucket_name}': {error_code} - {str(e)}")
                    # Không raise để không block việc khởi động app
        except ImportError:
            logger.warning("boto3 không được cài đặt, không thể tự động tạo bucket")
        except Exception as e:
            logger.error(f"Lỗi khi đảm bảo bucket tồn tại: {str(e)}")
            # Không raise exception để không block việc khởi động app
    
    def _save(self, name, content):
        """
        Override save method để log và xử lý lỗi
        Tự động tạo bucket nếu chưa tồn tại khi upload
        """
        try:
            logger.info(f"Uploading file to MinIO: {name}")
            result = super()._save(name, content)
            logger.info(f"Successfully uploaded to MinIO: {result}")
            return result
        except Exception as e:
            error_str = str(e)
            # Kiểm tra nếu lỗi là bucket không tồn tại
            if 'NoSuchBucket' in error_str or 'does not exist' in error_str.lower():
                logger.warning(f"Bucket không tồn tại, đang thử tạo bucket '{self.bucket_name}'...")
                try:
                    # Thử tạo bucket lại
                    self._ensure_bucket_exists()
                    # Retry upload
                    logger.info(f"Retrying upload after creating bucket: {name}")
                    result = super()._save(name, content)
                    logger.info(f"Successfully uploaded to MinIO after retry: {result}")
                    return result
                except Exception as retry_error:
                    logger.error(f"Failed to create bucket or retry upload: {str(retry_error)}")
                    raise
            else:
                logger.error(f"Failed to upload file to MinIO: {name}, Error: {error_str}")
                raise
    
    def url(self, name):
        """
        Override URL method để đảm bảo URL đúng format
        """
        if not name:
            return ''
        
        try:
            url = super().url(name)
            logger.debug(f"Generated MinIO URL for {name}: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate URL for {name}: {str(e)}")
            return ''
    
    def delete(self, name):
        """
        Override delete method để log
        """
        try:
            logger.info(f"Deleting file from MinIO: {name}")
            super().delete(name)
            logger.info(f"Successfully deleted from MinIO: {name}")
        except Exception as e:
            logger.error(f"Failed to delete file from MinIO: {name}, Error: {str(e)}")
            raise
    
    def get_available_name(self, name, max_length=None):
        """
        Tạo unique filename nếu file đã tồn tại để tránh overwrite
        Format: {base}_{uuid}{ext}
        """
        if self.exists(name):
            # File đã tồn tại, tạo unique name
            base, ext = os.path.splitext(name)
            unique_name = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
            return super().get_available_name(unique_name, max_length)
        return super().get_available_name(name, max_length)
