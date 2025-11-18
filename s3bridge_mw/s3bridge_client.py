"""
S3Bridge Midway Client Module
A modular S3 access approach with Midway authentication
"""

import boto3
import json
import io
import csv
import threading
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from typing import List, Optional, Dict, Any, BinaryIO, Union
from .s3bridge_auth import S3BridgeAuthProvider

class S3BridgeClient:
    """S3Bridge client with credential management and common operations"""
    
    def __init__(self, bucket_name: str, service_name: str = "default"):
        """
        Initialize S3 client with S3Bridge Midway authentication
        
        Args:
            bucket_name: Target S3 bucket name
            service_name: Service identifier for credential API
        """
        self.bucket_name = bucket_name
        self.service_name = service_name
        self._s3_client = None
        self._auth_provider = S3BridgeAuthProvider(service_name)
        
        # Validate bucket access for service
        self._validate_bucket_access()
        
    def _get_s3_client(self):
        """Get authenticated S3 client, refreshing credentials if needed"""
        if not self._s3_client or self._auth_provider.credentials_expired():
            credentials = self._auth_provider.get_credentials()
            session = boto3.Session(
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'],
                aws_session_token=credentials.get('session_token')
            )
            self._s3_client = session.client('s3')
        return self._s3_client

    
    def _validate_bucket_access(self):
        """Validate that service has access to the specified bucket"""
        # This will be populated dynamically by service configuration
        # For now, allow all buckets - validation happens at credential service level
        pass
    
    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self._get_s3_client().head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def read_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Read JSON file from S3"""
        try:
            response = self._get_s3_client().get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except (ClientError, json.JSONDecodeError):
            return None
    
    def write_json(self, data: Dict[str, Any], key: str) -> bool:
        """Write JSON data to S3"""
        try:
            json_data = json.dumps(data, indent=4)
            self._get_s3_client().put_object(
                Body=json_data,
                Bucket=self.bucket_name,
                Key=key,
                ContentType='application/json'
            )
            return True
        except ClientError:
            return False
    
    def read_text(self, key: str) -> Optional[str]:
        """Read text file from S3"""
        try:
            response = self._get_s3_client().get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read().decode('utf-8')
        except ClientError:
            return None
    
    def write_text(self, content: str, key: str) -> bool:
        """Write text content to S3"""
        try:
            self._get_s3_client().put_object(
                Body=content,
                Bucket=self.bucket_name,
                Key=key,
                ContentType='text/plain'
            )
            return True
        except ClientError:
            return False
    
    def upload_file(self, local_path: str, key: str) -> bool:
        """Upload file to S3"""
        try:
            self._get_s3_client().upload_file(local_path, self.bucket_name, key)
            return True
        except ClientError:
            return False
    
    def download_file(self, key: str, local_path: str) -> bool:
        """Download file from S3"""
        try:
            self._get_s3_client().download_file(self.bucket_name, key, local_path)
            return True
        except ClientError:
            return False
    
    def list_objects(self, prefix: str = '') -> List[str]:
        """List objects in bucket with optional prefix"""
        try:
            response = self._get_s3_client().list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError:
            return []
    
    def delete_object(self, key: str) -> bool:
        """Delete object from S3"""
        try:
            self._get_s3_client().delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def append_csv_row(self, key: str, row_data: List[str]) -> bool:
        """Append row to CSV file in S3"""
        try:
            existing_content = self.read_text(key) or ""
            output = io.StringIO()
            writer = csv.writer(output)
            
            if existing_content:
                output.write(existing_content)
                if not existing_content.endswith('\n'):
                    output.write('\n')
            
            writer.writerow(row_data)
            return self.write_text(output.getvalue(), key)
        except Exception:
            return False
    
    def write_async(self, content: str, key: str) -> None:
        """Write content to S3 asynchronously"""
        def _write():
            self.write_text(content, key)
        threading.Thread(target=_write, daemon=True).start()