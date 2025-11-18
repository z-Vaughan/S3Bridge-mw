#!/usr/bin/env python3
"""
List Services Script
Shows all registered services in Universal S3 Library
"""

import boto3
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.aws_config import AWSConfig

def list_services():
    """List all registered services"""
    
    config = AWSConfig()
    
    if not config.is_deployed():
        print("Universal S3 Library not deployed. Run setup first.")
        return False
    
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_configuration(FunctionName='s3bridge-mw-credential-service')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        services = {}
        for key, value in env_vars.items():
            if key.startswith('SERVICE_'):
                service_name = key[8:].lower()
                try:
                    services[service_name] = json.loads(value)
                except json.JSONDecodeError:
                    continue
        
        # Add universal service if admin username is set
        admin_username = env_vars.get('ADMIN_USERNAME')
        if admin_username:
            services['universal'] = {
                'role': f"arn:aws:iam::{env_vars.get('AWS_ACCOUNT_ID', 'unknown')}:role/service-role/universal-s3-access-role",
                'buckets': ['*'],
                'restricted_users': [admin_username]
            }
        
        print("Universal S3 Library Services:")
        print("=" * 50)
        
        if not services:
            print("No services configured yet.")
            print("\\nAdd services with:")
            print("   python scripts/add_service.py myapp 'myapp-*'")
        else:
            for service_name, config in services.items():
                print(f"\\nService: {service_name}")
                print(f"  Role: {config['role']}")
                print(f"  Buckets: {', '.join(config['buckets'])}")
                if 'restricted_users' in config:
                    print(f"  Restricted Users: {', '.join(config['restricted_users'])}")
        
        return True
        
    except Exception as e:
        print(f"Failed to list services: {e}")
        return False

def main():
    success = list_services()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())