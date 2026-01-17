"""
Test AWS S3 connection and configuration

Usage:
    python scripts/test_s3_connection.py
"""
import os
import sys
from pathlib import Path
from io import BytesIO

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

import boto3
from botocore.exceptions import ClientError
from decouple import config


def test_s3_connection():
    """Test S3 connection and permissions"""
    print("=" * 80)
    print("AWS S3 Connection Test")
    print("=" * 80)
    
    # Get credentials from .env
    access_key = config('AWS_ACCESS_KEY_ID', default=None)
    secret_key = config('AWS_SECRET_ACCESS_KEY', default=None)
    bucket_name = config('AWS_STORAGE_BUCKET_NAME', default='restaurant-vuhieu2402')
    region = config('AWS_S3_REGION_NAME', default='ap-northeast-1')
    cloudfront_domain = config('AWS_S3_CUSTOM_DOMAIN', default=None)
    
    print(f"\nConfiguration:")
    print(f"  Bucket: {bucket_name}")
    print(f"  Region: {region}")
    if cloudfront_domain:
        print(f"  CloudFront: {cloudfront_domain}")
    print(f"  Access Key: {access_key[:10]}***" if access_key else "  Access Key: NOT SET")
    
    if not access_key or not secret_key:
        print("\n❌ AWS credentials not found!")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        return False
    
    # Create S3 client
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        print("\n✓ S3 client created")
    except Exception as e:
        print(f"\n❌ Failed to create S3 client: {e}")
        return False
    
    # Test 1: Check if bucket exists
    print("\n" + "-" * 80)
    print("Test 1: Checking bucket existence...")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ Bucket '{bucket_name}' exists and is accessible")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            print(f"❌ Bucket '{bucket_name}' does not exist")
        elif error_code == '403':
            print(f"❌ Access denied to bucket '{bucket_name}'")
            print("   Check your IAM permissions")
        else:
            print(f"❌ Error: {e}")
        return False
    
    # Test 2: List objects (permission check)
    print("\n" + "-" * 80)
    print("Test 2: Testing list permission...")
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        count = response.get('KeyCount', 0)
        print(f"✓ Can list objects ({count} objects found)")
        
        if count > 0:
            print("\n  Sample files:")
            for obj in response.get('Contents', [])[:5]:
                size_kb = obj['Size'] / 1024
                print(f"    - {obj['Key']} ({size_kb:.2f} KB)")
    except ClientError as e:
        print(f"❌ Cannot list objects: {e}")
        return False
    
    # Test 3: Upload test file
    print("\n" + "-" * 80)
    print("Test 3: Testing upload permission...")
    test_key = 'media/test/connection_test.txt'
    test_content = b'AWS S3 connection test - OK'
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=BytesIO(test_content),
            ContentType='text/plain'
            # ACL removed - use bucket policy instead
        )
        print(f"✓ Successfully uploaded test file: {test_key}")
    except ClientError as e:
        print(f"❌ Cannot upload file: {e}")
        print("   Check your IAM policy includes s3:PutObject")
        return False
    
    # Test 4: Read test file
    print("\n" + "-" * 80)
    print("Test 4: Testing read permission...")
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        content = response['Body'].read()
        if content == test_content:
            print(f"✓ Successfully read test file")
        else:
            print(f"❌ File content mismatch")
            return False
    except ClientError as e:
        print(f"❌ Cannot read file: {e}")
        return False
    
    # Test 5: Generate URL
    print("\n" + "-" * 80)
    print("Test 5: Testing URL generation...")
    try:
        if cloudfront_domain:
            url = f"https://{cloudfront_domain}/{test_key}"
            print(f"✓ CloudFront URL: {url}")
        else:
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{test_key}"
            print(f"✓ S3 URL: {url}")
        
        print("\n  Try accessing this URL in your browser to verify public access")
    except Exception as e:
        print(f"❌ URL generation failed: {e}")
    
    # Test 6: Delete test file
    print("\n" + "-" * 80)
    print("Test 6: Testing delete permission...")
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"✓ Successfully deleted test file")
    except ClientError as e:
        print(f"❌ Cannot delete file: {e}")
        print(f"   Please manually delete: {test_key}")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\nYour S3 configuration is working perfectly!")
    print("\nNext steps:")
    print("1. Run migration: python scripts/migrate_minio_to_s3.py")
    print("2. Update settings to use S3")
    print("3. Restart application")
    
    return True


if __name__ == '__main__':
    try:
        success = test_s3_connection()
        
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

