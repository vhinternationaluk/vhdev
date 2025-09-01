import boto3
import os
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

def upload_file_to_s3(file, folder_name="products_images"):
    """
    Enhanced S3 upload with detailed error reporting
    """
    try:
        # Debug: Log environment variables (remove after debugging)
        logger.info("=== S3 Upload Debug Info ===")
        logger.info(f"AWS_ACCESS_KEY_ID exists: {bool(os.environ.get('AWS_ACCESS_KEY_ID'))}")
        logger.info(f"AWS_SECRET_ACCESS_KEY exists: {bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))}")
        logger.info(f"AWS_STORAGE_BUCKET_NAME: {os.environ.get('AWS_STORAGE_BUCKET_NAME')}")
        logger.info(f"AWS_S3_REGION_NAME: {os.environ.get('AWS_S3_REGION_NAME')}")
        logger.info(f"File name: {file.name}")
        logger.info(f"File size: {file.size}")
        logger.info(f"File content type: {file.content_type}")
        
        # Validate environment variables
        required_vars = {
            'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
            'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
            'AWS_STORAGE_BUCKET_NAME': os.environ.get('AWS_STORAGE_BUCKET_NAME'),
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            return {'success': False, 'error': f'Missing AWS config: {missing_vars}'}
        
        # Initialize S3 client with explicit credentials
        logger.info("Initializing S3 client...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=required_vars['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=required_vars['AWS_SECRET_ACCESS_KEY'],
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
        )
        
        # Test S3 connection first
        logger.info("Testing S3 connection...")
        try:
            s3_client.head_bucket(Bucket=required_vars['AWS_STORAGE_BUCKET_NAME'])
            logger.info("S3 bucket access confirmed")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 bucket access failed: {error_code} - {e}")
            return {'success': False, 'error': f'S3 bucket access denied: {error_code}'}
        
        # Generate unique filename
        file_extension = file.name.split('.')[-1].lower()
        unique_filename = f"{folder_name}/{uuid.uuid4()}.{file_extension}"
        
        logger.info(f"Uploading to: {unique_filename}")
        
        # Reset file pointer to beginning
        file.seek(0)
        
        # Upload file
        s3_client.upload_fileobj(
            file,
            required_vars['AWS_STORAGE_BUCKET_NAME'],
            unique_filename,
            ExtraArgs={
                'ContentType': file.content_type or 'image/jpeg',

            }
        )
        
        # Generate S3 URL
        s3_url = f"https://{required_vars['AWS_STORAGE_BUCKET_NAME']}.s3.amazonaws.com/{unique_filename}"
        
        logger.info(f"Upload successful! URL: {s3_url}")
        return  s3_url
        
    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return {'success': False, 'error': 'AWS credentials not found'}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS ClientError: {error_code} - {error_message}")
        return {'success': False, 'error': f'AWS Error: {error_code} - {error_message}'}
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        return {'success': False, 'error': f'Upload error: {str(e)}'}
