"""
Universal Authentication Provider
Account-agnostic Midway authentication and credential management
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add config to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.aws_config import AWSConfig

class UniversalAuthProvider:
    """Universal authentication provider for AWS credentials via Midway"""
    
    def __init__(self, service_name: str = "default"):
        """
        Initialize auth provider
        
        Args:
            service_name: Service identifier for credential API
        """
        self.service_name = service_name
        self._cached_credentials = None
        self._credentials_expiry = None
        self._config = AWSConfig()
        
    def get_credentials(self) -> Dict[str, Any]:
        """Get AWS credentials via Midway authentication"""
        if self._cached_credentials and not self.credentials_expired():
            return self._cached_credentials
            
        return self._fetch_fresh_credentials()
    
    def credentials_expired(self) -> bool:
        """Check if cached credentials are expired"""
        if not self._credentials_expiry:
            return True
        return datetime.now(self._credentials_expiry.tzinfo) >= self._credentials_expiry
    
    def _fetch_fresh_credentials(self) -> Dict[str, Any]:
        """Fetch fresh credentials from API"""
        
        # Check if infrastructure is deployed
        if not self._config.is_deployed():
            raise Exception("Universal S3 Library not deployed. Run: python -m universal_s3_library.setup")
        
        # Get API Gateway URL
        api_url = self._config.get_api_gateway_url()
        if not api_url:
            raise Exception("API Gateway URL not found. Check deployment.")
        
        endpoint = f"{api_url}/credentials"
        
        # Get Midway cookies
        cookies = self._get_midway_cookies()
        cookie_string = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        try:
            response = requests.get(
                endpoint,
                params={'service': self.service_name, 'duration': '3600'},
                headers={'Cookie': cookie_string},
                timeout=30
            )
            
            if response.status_code == 200:
                creds_data = response.json()
                
                # Cache credentials
                self._cached_credentials = {
                    'access_key': creds_data['AccessKeyId'],
                    'secret_key': creds_data['SecretAccessKey'],
                    'session_token': creds_data['SessionToken']
                }
                
                # Set expiry (10 minutes before actual expiry)
                expiry_time = datetime.fromisoformat(creds_data['Expiration'].replace('Z', '+00:00'))
                self._credentials_expiry = expiry_time - timedelta(minutes=10)
                
                return self._cached_credentials
            else:
                raise Exception(f"Credential service failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Universal credential service failed: {str(e)}")
    
    def _get_midway_cookies(self) -> Dict[str, str]:
        """Get Midway cookies from cookie file"""
        cookie_path = os.path.join(os.path.expanduser('~'), '.midway', 'cookie')
        
        # Check if cookie exists
        if not os.path.exists(cookie_path):
            print("No Midway cookie found. Running 'mwinit -o'...")
            result = os.system('mwinit -o')
            if result != 0:
                raise Exception("Midway authentication failed")
        
        # Check if cookie is expired
        if self._is_cookie_expired(cookie_path):
            print("Midway cookie expired. Running 'mwinit -o'...")
            result = os.system('mwinit -o')
            if result != 0:
                raise Exception("Midway authentication failed")
        
        # Parse cookies
        cookies = {}
        with open(cookie_path, 'r') as f:
            for line in f:
                if '\\t' in line:
                    parts = line.strip().split('\\t')
                    if len(parts) >= 7:
                        name, value = parts[5], parts[6]
                        if name in ['amazon_enterprise_access', 'session']:
                            cookies[name] = value
        
        if not cookies:
            raise Exception("Required Midway cookies not found")
        
        return cookies
    
    def _is_cookie_expired(self, cookie_path: str) -> bool:
        """Check if Midway cookie is expired"""
        try:
            with open(cookie_path, 'r') as f:
                for line in f:
                    if 'amazon_enterprise_access' in line:
                        parts = line.split('\\t')
                        if len(parts) >= 5:
                            expiry = int(parts[4])
                            return datetime.now().timestamp() >= expiry
        except Exception:
            return True
        
        return False
    
    def invalidate_credentials(self):
        """Force refresh of cached credentials"""
        self._cached_credentials = None
        self._credentials_expiry = None
    
    def reset_authentication(self):
        """Reset authentication state"""
        self.invalidate_credentials()