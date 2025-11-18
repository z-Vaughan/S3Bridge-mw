"""
AWS Configuration Management
Auto-detects account settings and manages deployment configuration
"""

import boto3
import json
import os
from pathlib import Path

class AWSConfig:
    """Dynamic AWS configuration based on current account"""
    
    def __init__(self):
        self._sts = boto3.client('sts')
        self._session = boto3.Session()
        
    @property
    def account_id(self):
        """Get current AWS account ID"""
        return self._sts.get_caller_identity()['Account']
    
    @property
    def region(self):
        """Get current AWS region"""
        return self._session.region_name or 'us-east-1'
    
    @property
    def lambda_role_arn(self):
        """Lambda execution role ARN"""
        return f"arn:aws:iam::{self.account_id}:role/s3bridge-mw-lambda-role"
    
    def service_role_arn(self, service_name):
        """Service-specific IAM role ARN"""
        return f"arn:aws:iam::{self.account_id}:role/service-role/{service_name}-s3-access-role"
    
    @property
    def stack_name(self):
        """CloudFormation stack name"""
        return "s3bridge-mw"
    
    def get_api_gateway_url(self):
        """Get deployed API Gateway URL from CloudFormation"""
        try:
            cf = boto3.client('cloudformation')
            outputs = cf.describe_stacks(StackName=self.stack_name)['Stacks'][0]['Outputs']
            return next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'ApiGatewayUrl')
        except Exception:
            return None
    
    def save_deployment_config(self, api_url, admin_username):
        """Save deployment configuration"""
        config_file = Path(__file__).parent / 'deployment.json'
        config = {
            'account_id': self.account_id,
            'region': self.region,
            'api_gateway_url': api_url,
            'admin_username': admin_username,
            'stack_name': self.stack_name
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_deployment_config(self):
        """Load saved deployment configuration"""
        config_file = Path(__file__).parent / 'deployment.json'
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return None
    
    def is_deployed(self):
        """Check if infrastructure is deployed"""
        try:
            cf = boto3.client('cloudformation')
            cf.describe_stacks(StackName=self.stack_name)
            return True
        except Exception:
            return False