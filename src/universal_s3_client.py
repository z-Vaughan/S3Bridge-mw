"""
Universal S3 Client
Account-agnostic S3 client with automatic credential management
"""

import boto3
import json
import fnmatch
from typing import Dict, Any, List, Optional
from .universal_auth import UniversalAuthProvider

class UniversalS3Client:
    """Universal S3 client with service-based access control"""
    
    def __init__(self, bucket_name: str, service_name: str):
        """
        Initialize S3 client for specific service
        
        Args:
            bucket_name: S3 bucket name
            service_name: Service identifier (determines permissions)
        """
        self.bucket_name = bucket_name
        self.service_name = service_name
        self.auth_provider = UniversalAuthProvider(service_name)
        self._s3_client = None
        
        # Validate bucket access for service
        self._validate_bucket_access()
    
    def _validate_bucket_access(self):
        """Validate that service can access this bucket"""
        # Note: In modular version, this could be loaded from config
        # For now, using basic validation
        service_patterns = {
            'analytics': ['*-analytics-*', 'analytics-*'],
            'universal': ['*']  # Universal access
        }
        
        patterns = service_patterns.get(self.service_name, [f"{self.service_name}-*"])
        
        # Check if bucket matches any allowed pattern
        if not any(fnmatch.fnmatch(self.bucket_name, pattern) for pattern in patterns):
            if self.service_name != 'universal':  # Universal service bypasses validation
                raise ValueError(f"Service '{self.service_name}' not authorized for bucket '{self.bucket_name}'")
    
    def _get_s3_client(self):
        """Get authenticated S3 client"""
        if not self._s3_client:
            credentials = self.auth_provider.get_credentials()
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'],
                aws_session_token=credentials['session_token']
            )
        return self._s3_client
    
    def _refresh_client_if_needed(self):
        """Refresh S3 client if credentials expired"""
        if self.auth_provider.credentials_expired():
            self._s3_client = None
    
    # S3 Operations
    def file_exists(self, key: str) -> bool:
        """Check if file exists in bucket"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except s3.exceptions.NoSuchKey:
            return False
    
    def read_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Read JSON file from S3"""
        try:
            content = self.read_text(key)
            return json.loads(content) if content else None
        except json.JSONDecodeError:
            return None
    
    def write_json(self, data: Dict[str, Any], key: str) -> bool:
        """Write JSON data to S3"""
        try:
            content = json.dumps(data, indent=2)
            return self.write_text(content, key)
        except Exception:
            return False
    
    def read_text(self, key: str) -> Optional[str]:
        """Read text file from S3"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            response = s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read().decode('utf-8')
        except Exception:
            return None
    
    def write_text(self, content: str, key: str) -> bool:
        """Write text content to S3"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/plain'
            )
            return True
        except Exception:
            return False
    
    def upload_file(self, local_path: str, key: str) -> bool:
        """Upload file to S3"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            s3.upload_file(local_path, self.bucket_name, key)
            return True
        except Exception:
            return False
    
    def download_file(self, key: str, local_path: str) -> bool:
        """Download file from S3"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            s3.download_file(self.bucket_name, key, local_path)
            return True
        except Exception:
            return False
    
    def list_objects(self, prefix: str = "") -> List[str]:
        """List objects in bucket with prefix"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            
            objects = []
            paginator = s3.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    objects.extend([obj['Key'] for obj in page['Contents']])
            
            return objects
        except Exception:
            return []
    
    def delete_object(self, key: str) -> bool:
        """Delete object from S3"""
        try:
            self._refresh_client_if_needed()
            s3 = self._get_s3_client()
            s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False