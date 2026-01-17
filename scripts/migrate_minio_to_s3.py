"""
Migrate all files from MinIO to AWS S3

Usage:
    python scripts/migrate_minio_to_s3.py

Requirements:
    pip install boto3 tqdm
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

import boto3
from botocore.exceptions import ClientError
from decouple import config

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠️  tqdm not installed. Install for progress bar: pip install tqdm")

# Setup logging
log_dir = BASE_DIR / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MinIOToS3Migrator:
    """Migrate files from MinIO to AWS S3"""
    
    def __init__(self):
        # MinIO Configuration
        self.minio_endpoint = config('MINIO_ENDPOINT_URL', default='http://localhost:9000')
        self.minio_access_key = config('MINIO_ACCESS_KEY', default='minioadmin')
        self.minio_secret_key = config('MINIO_SECRET_KEY', default='minioadmin123')
        self.minio_bucket = config('MINIO_BUCKET_NAME', default='restaurant-media')
        
        # AWS S3 Configuration
        self.s3_access_key = config('AWS_ACCESS_KEY_ID')
        self.s3_secret_key = config('AWS_SECRET_ACCESS_KEY')
        self.s3_bucket = config('AWS_STORAGE_BUCKET_NAME', default='restaurant-vuhieu2402')
        self.s3_region = config('AWS_S3_REGION_NAME', default='ap-northeast-1')
        
        # Validate credentials
        if not self.s3_access_key or not self.s3_secret_key:
            raise ValueError("AWS credentials not found! Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        
        # MinIO client
        logger.info(f"Connecting to MinIO: {self.minio_endpoint}")
        try:
            self.minio_client = boto3.client(
                's3',
                endpoint_url=self.minio_endpoint,
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key,
                region_name='us-east-1'
            )
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")
            logger.error("Make sure MinIO is running: docker-compose up -d minio")
            raise
        
        # AWS S3 client
        logger.info(f"Connecting to AWS S3: {self.s3_bucket} ({self.s3_region})")
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key,
            region_name=self.s3_region
        )
        
        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0,
            'errors': []
        }
    
    def list_minio_files(self):
        """List all files in MinIO bucket"""
        logger.info(f"Listing files in MinIO bucket: {self.minio_bucket}")
        
        files = []
        try:
            paginator = self.minio_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.minio_bucket):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'modified': obj['LastModified']
                        })
                        self.stats['total_size'] += obj['Size']
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchBucket':
                logger.error(f"MinIO bucket '{self.minio_bucket}' does not exist!")
                logger.error("Please make sure MinIO is running and bucket exists")
                raise
            else:
                logger.error(f"Error listing MinIO files: {e}")
                raise
        
        logger.info(f"Found {len(files)} files in MinIO (Total size: {self.stats['total_size'] / 1024 / 1024:.2f} MB)")
        return files
    
    def file_exists_in_s3(self, key):
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=key)
            return True
        except ClientError:
            return False
    
    def get_content_type(self, filename):
        """Guess content type from filename"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    def copy_file(self, key, size, skip_existing=True):
        """Copy single file from MinIO to S3"""
        try:
            # Check if exists in S3
            if skip_existing and self.file_exists_in_s3(key):
                logger.debug(f"⊘ Skipping (already exists): {key}")
                self.stats['skipped'] += 1
                return True
            
            # Download from MinIO
            logger.debug(f"↓ Downloading from MinIO: {key}")
            response = self.minio_client.get_object(
                Bucket=self.minio_bucket,
                Key=key
            )
            file_content = response['Body'].read()
            content_type = response.get('ContentType') or self.get_content_type(key)
            
            # Upload to S3
            logger.debug(f"↑ Uploading to S3: {key}")
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type
                # ACL removed - use bucket policy instead
            )
            
            size_mb = size / 1024 / 1024
            logger.info(f"✓ Copied: {key} ({size_mb:.2f} MB)")
            self.stats['success'] += 1
            return True
            
        except Exception as e:
            error_msg = f"✗ Failed to copy {key}: {str(e)}"
            logger.error(error_msg)
            self.stats['failed'] += 1
            self.stats['errors'].append({'key': key, 'error': str(e)})
            return False
    
    def migrate_all(self, skip_existing=True):
        """Migrate all files from MinIO to S3"""
        files = self.list_minio_files()
        self.stats['total'] = len(files)
        
        if not files:
            logger.warning("No files found in MinIO bucket!")
            return True
        
        logger.info("=" * 80)
        logger.info(f"Starting migration: {len(files)} files")
        logger.info(f"Source: MinIO ({self.minio_bucket})")
        logger.info(f"Destination: S3 ({self.s3_bucket})")
        logger.info("=" * 80)
        
        # Progress bar
        if HAS_TQDM:
            iterator = tqdm(files, desc="Migrating", unit="file")
        else:
            iterator = files
            print(f"Migrating {len(files)} files...")
        
        for i, file_info in enumerate(iterator, 1):
            self.copy_file(
                file_info['key'],
                file_info['size'],
                skip_existing=skip_existing
            )
            if not HAS_TQDM:
                if i % 10 == 0:
                    print(f"Progress: {i}/{len(files)} files")
        
        # Print summary
        logger.info("=" * 80)
        logger.info("MIGRATION SUMMARY:")
        logger.info(f"  Total files: {self.stats['total']}")
        logger.info(f"  ✓ Success: {self.stats['success']}")
        logger.info(f"  ⊘ Skipped: {self.stats['skipped']}")
        logger.info(f"  ✗ Failed: {self.stats['failed']}")
        logger.info(f"  Total size: {self.stats['total_size'] / 1024 / 1024:.2f} MB")
        logger.info("=" * 80)
        
        if self.stats['errors']:
            logger.error(f"\n❌ {len(self.stats['errors'])} ERRORS:")
            for i, error in enumerate(self.stats['errors'][:10], 1):
                logger.error(f"  {i}. {error['key']}: {error['error']}")
            if len(self.stats['errors']) > 10:
                logger.error(f"  ... and {len(self.stats['errors']) - 10} more errors")
        
        return self.stats['failed'] == 0
    
    def verify_migration(self):
        """Verify all files copied successfully"""
        logger.info("\n" + "=" * 80)
        logger.info("VERIFYING MIGRATION...")
        logger.info("=" * 80)
        
        minio_files = self.list_minio_files()
        missing = []
        
        if HAS_TQDM:
            iterator = tqdm(minio_files, desc="Verifying", unit="file")
        else:
            iterator = minio_files
            print("Verifying files...")
        
        for file_info in iterator:
            if not self.file_exists_in_s3(file_info['key']):
                missing.append(file_info['key'])
        
        if missing:
            logger.error(f"❌ {len(missing)} files missing in S3:")
            for key in missing[:20]:
                logger.error(f"  - {key}")
            if len(missing) > 20:
                logger.error(f"  ... and {len(missing) - 20} more")
            return False
        else:
            logger.info("✅ All files verified successfully!")
            logger.info(f"   {len(minio_files)} files are present in S3")
            return True


def main():
    """Main migration script"""
    print("=" * 80)
    print("MinIO → AWS S3 Migration Tool")
    print("=" * 80)
    
    try:
        migrator = MinIOToS3Migrator()
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        print("\nPlease check:")
        print("1. MinIO is running: docker-compose ps minio")
        print("2. AWS credentials are set in .env file")
        print("3. S3 bucket exists and is accessible")
        return
    
    # Show configuration
    print(f"\nSource: MinIO")
    print(f"  - Endpoint: {migrator.minio_endpoint}")
    print(f"  - Bucket: {migrator.minio_bucket}")
    print(f"\nDestination: AWS S3")
    print(f"  - Bucket: {migrator.s3_bucket}")
    print(f"  - Region: {migrator.s3_region}")
    print(f"\nLog file: {log_file}")
    
    # Ask confirmation
    print("\n⚠️  This will copy all files from MinIO to S3")
    print("   Existing files in S3 will be skipped (no overwrite)")
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Migration cancelled.")
        return
    
    # Run migration
    print("\n")
    success = migrator.migrate_all(skip_existing=True)
    
    if success:
        # Verify
        print("\n")
        verified = migrator.verify_migration()
        
        if verified:
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("\nNext steps:")
            print("1. Restart Django: docker-compose restart django celery_worker")
            print("2. Test file uploads: python manage.py shell")
            print("3. Check application for broken images")
            print(f"\nLog saved to: {log_file}")
        else:
            print("\n❌ Verification failed - some files are missing")
            print(f"Please check the log file: {log_file}")
    else:
        print("\n❌ Migration failed - check the log file for errors")
        print(f"Log file: {log_file}")


if __name__ == '__main__':
    main()

