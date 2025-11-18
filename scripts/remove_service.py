#!/usr/bin/env python3
"""
Remove Service Script
Removes service from Universal S3 Library
"""

import boto3
import json
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.aws_config import AWSConfig

def remove_service(service_name, force=False):
    """Remove service from Universal S3 Library"""
    
    config = AWSConfig()
    
    if not config.is_deployed():
        print("Universal S3 Library not deployed. Run setup first.")
        return False
    
    try:
        lambda_client = boto3.client('lambda')
        iam = boto3.client('iam')
        
        # Get current environment variables
        response = lambda_client.get_function_configuration(FunctionName='s3bridge-mw-credential-service')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        service_env_key = f'SERVICE_{service_name.upper()}'
        
        if service_env_key not in env_vars:
            print(f"Service '{service_name}' not found")
            return False
        
        if not force:
            print(f"Remove service '{service_name}'?")
            confirm = input("This will delete the IAM role and Lambda configuration (y/N): ").lower().strip()
            if confirm != 'y':
                print("Service removal cancelled")
                return False
        
        # Remove from Lambda environment
        del env_vars[service_env_key]
        lambda_client.update_function_configuration(
            FunctionName='s3bridge-mw-credential-service',
            Environment={'Variables': env_vars}
        )
        print(f"Removed Lambda configuration for service: {service_name}")
        
        # Remove IAM role
        role_name = f"{service_name}-s3-access-role"
        try:
            # Delete role policy first
            iam.delete_role_policy(
                RoleName=role_name,
                PolicyName=f"{service_name}S3AccessPolicy"
            )
            # Delete role
            iam.delete_role(RoleName=role_name)
            print(f"Removed IAM role: {role_name}")
        except iam.exceptions.NoSuchEntityException:
            print(f"IAM role {role_name} not found (already deleted)")
        
        print(f"Service '{service_name}' removed successfully")
        return True
        
    except Exception as e:
        print(f"Failed to remove service: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Remove service from Universal S3 Library')
    parser.add_argument('service_name', help='Service name to remove')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    args = parser.parse_args()
    
    success = remove_service(args.service_name, args.force)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())