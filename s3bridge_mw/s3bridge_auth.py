"""
S3Bridge Midway Authentication Provider
Handles Midway authentication and credential management for any service
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

class S3BridgeAuthProvider:
    """S3Bridge authentication provider for AWS credentials via Midway"""
    
    def __init__(self, service_name: str = "default"):
        """
        Initialize auth provider
        
        Args:
            service_name: Service identifier for credential API
        """
        self.service_name = service_name
        self._cached_credentials = None
        self._credentials_expiry = None
        
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
    
    def _get_api_endpoint(self) -> str:
        """Get S3Bridge Midway API endpoint"""
        # Try to load from deployment config
        config_file = Path(__file__).parent.parent / "config" / "deployment.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                    api_url = config.get('api_gateway_url')
                    if api_url:
                        return f"{api_url}/credentials"
            except Exception:
                pass
        
        # Fallback - this should be set during deployment
        raise Exception("S3Bridge Midway not deployed. Run: s3bridge-mw setup")
    
    def _get_midway_cookies(self) -> str:
        """Get Midway cookies from browser or environment"""
        # Try environment variables first
        cookies = os.environ.get('MIDWAY_COOKIES')
        if cookies:
            return cookies
            
        # Try to read from browser cookies (simplified)
        # In production, this would integrate with actual Midway authentication
        cookie_sources = [
            os.path.expanduser("~/.midway_cookies"),
            "/tmp/midway_cookies"
        ]
        
        for cookie_file in cookie_sources:
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file) as f:
                        return f.read().strip()
                except Exception:
                    continue
        
        raise Exception("Midway authentication required. Please authenticate via Midway.")
    
    def _fetch_fresh_credentials(self) -> Dict[str, Any]:
        """Fetch fresh credentials from API"""
        endpoint = self._get_api_endpoint()
        cookies = self._get_midway_cookies()
        
        try:
            response = requests.get(
                endpoint,
                params={'service': self.service_name, 'duration': '3600'},
                headers={'Cookie': cookies},
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
            raise Exception(f"S3Bridge Midway credential service failed: {str(e)}")
    
    def invalidate_credentials(self):
        """Force refresh of cached credentials"""
        self._cached_credentials = None
        self._credentials_expiry = None
    
    def reset_authentication(self):
        """Reset authentication state"""
        self.invalidate_credentials()