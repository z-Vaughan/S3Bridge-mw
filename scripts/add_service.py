#!/usr/bin/env python3
"""
Add Service Script
Creates IAM role and updates Lambda configuration for new service
"""

import boto3
import json
import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.aws_config import AWSConfig

def find_existing_api_gateway():
    """Find existing API Gateway that uses universal-credential-service"""
    try:
        api_client = boto3.client('apigateway')
        lambda_client = boto3.client('lambda')
        
        # Get s3bridge-mw-credential-service function ARN
        try:
            func_response = lambda_client.get_function(FunctionName='s3bridge-mw-credential-service')
            target_function_arn = func_response['Configuration']['FunctionArn']
        except lambda_client.exceptions.ResourceNotFoundException:
            return None
        
        # List all APIs
        apis = api_client.get_rest_apis()
        
        for api in apis['items']:
            api_id = api['id']
            try:
                # Get resources for this API
                resources = api_client.get_resources(restApiId=api_id)
                
                for resource in resources['items']:
                    # Check if this resource has GET method
                    if 'GET' in resource.get('resourceMethods', {}):
                        try:
                            # Get integration for GET method
                            integration = api_client.get_integration(
                                restApiId=api_id,
                                resourceId=resource['id'],
                                httpMethod='GET'
                            )
                            
                            # Check if integration points to our Lambda function
                            integration_uri = integration.get('uri', '')
                            if 's3bridge-mw-credential-service' in integration_uri:
                                return api_id
                                
                        except Exception:
                            continue
                            
            except Exception:
                continue
                
        return None
        
    except Exception as e:
        print(f"Could not search for existing API Gateway: {e}")
        return None

def create_service_role(service_name, bucket_patterns, permissions, config):
    """Create IAM role for service"""
    
    iam = boto3.client('iam')
    role_name = f"{service_name}-s3-access-role"
    
    # S3 permissions based on access level
    s3_actions = {
        'read-only': ['s3:GetObject', 's3:ListBucket'],
        'read-write': ['s3:GetObject', 's3:PutObject', 's3:DeleteObject', 's3:ListBucket'],
        'admin': ['s3:*']
    }
    
    # Create S3 resources from bucket patterns
    s3_resources = []
    for pattern in bucket_patterns:
        s3_resources.extend([
            f"arn:aws:s3:::{pattern}",
            f"arn:aws:s3:::{pattern}/*"
        ])
    
    # IAM policy document
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": s3_actions[permissions],
            "Resource": s3_resources
        }]
    }
    
    # Trust policy for Lambda role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": config.lambda_role_arn},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        # Create role
        iam.create_role(
            RoleName=role_name,
            Path='/service-role/',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Universal S3 Library service role for {service_name}"
        )
        
        # Attach policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{service_name}S3AccessPolicy",
            PolicyDocument=json.dumps(policy_doc)
        )
        
        print(f"Created IAM role: {role_name}")
        return config.service_role_arn(service_name)
        
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"Role {role_name} already exists, updating policy...")
        
        # Update existing policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{service_name}S3AccessPolicy",
            PolicyDocument=json.dumps(policy_doc)
        )
        
        return config.service_role_arn(service_name)

def update_lambda_config_only(service_name, bucket_patterns, role_arn, restricted_users, force=False):
    """Update Lambda environment variables instead of code"""
    
    lambda_client = boto3.client('lambda')
    
    try:
        # Get current environment variables
        response = lambda_client.get_function_configuration(FunctionName='s3bridge-mw-credential-service')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        # Check if service already exists
        service_env_key = f'SERVICE_{service_name.upper()}'
        if service_env_key in env_vars and not force:
            print(f"\\nService '{service_name}' already exists")
            overwrite = input("Overwrite existing service? (y/N): ").lower().strip()
            if overwrite != 'y':
                print("Service addition cancelled")
                return False
        
        # Add service as environment variable
        service_config = {
            'role': role_arn,
            'buckets': bucket_patterns
        }
        
        if restricted_users:
            service_config['restricted_users'] = restricted_users
        
        env_vars[service_env_key] = json.dumps(service_config)
        
        # Update Lambda environment
        lambda_client.update_function_configuration(
            FunctionName='s3bridge-mw-credential-service',
            Environment={'Variables': env_vars}
        )
        
        print(f"Updated Lambda environment for service: {service_name}")
        return True
        
    except Exception as e:
        print(f"Failed to update Lambda environment: {e}")
        return False

def check_and_create_buckets(bucket_patterns):
    """Check if buckets exist and offer to create them"""
    s3 = boto3.client('s3')
    
    # Extract actual bucket names from patterns (remove wildcards)
    bucket_names = []
    for pattern in bucket_patterns:
        if '*' not in pattern:
            bucket_names.append(pattern)
    
    if not bucket_names:
        return  # Only wildcard patterns, can't pre-create
    
    missing_buckets = []
    for bucket in bucket_names:
        try:
            s3.head_bucket(Bucket=bucket)
        except s3.exceptions.NoSuchBucket:
            missing_buckets.append(bucket)
        except Exception:
            pass  # Access denied or other error, assume exists
    
    if missing_buckets:
        print(f"\\nMissing buckets: {', '.join(missing_buckets)}")
        create = input("Create missing buckets? (y/N): ").lower().strip()
        
        if create == 'y':
            for bucket in missing_buckets:
                try:
                    s3.create_bucket(Bucket=bucket)
                    print(f"Created bucket: {bucket}")
                except Exception as e:
                    print(f"Failed to create {bucket}: {e}")

def add_service(service_name, bucket_patterns, permissions='read-write', restricted_users=None, force=False):
    """Add new service to Universal S3 Library"""
    
    config = AWSConfig()
    
    # Check if infrastructure is deployed (either CloudFormation or existing API Gateway)
    existing_api = find_existing_api_gateway()
    if not config.is_deployed() and not existing_api:
        print("Universal S3 Library not deployed. Run setup first:")
        print("   python scripts/setup.py")
        return False
    
    print(f"Adding service: {service_name}")
    print(f"Bucket patterns: {bucket_patterns}")
    print(f"Permissions: {permissions}")
    
    if restricted_users:
        print(f"Restricted to users: {restricted_users}")
    
    # Check and optionally create buckets
    check_and_create_buckets(bucket_patterns)
    
    try:
        # Create IAM role
        role_arn = create_service_role(service_name, bucket_patterns, permissions, config)
        
        # Check for existing API Gateway
        existing_api = find_existing_api_gateway()
        if existing_api:
            print(f"Found existing API Gateway: {existing_api}")
            print(f"Will update existing endpoint instead of creating new one")
            # Update Lambda environment variables
            success = update_lambda_config_only(service_name, bucket_patterns, role_arn, restricted_users, force)
            if not success:
                return False
            
            # Deploy Lambda changes only
            print(f"Deploying Lambda changes only...")
            import subprocess
            result = subprocess.run([sys.executable, str(Path(__file__).parent / 'deploy_lambda_only.py')], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Lambda deployment successful")
            else:
                print(f"Lambda deployment failed: {result.stderr}")
                return False
        else:
            print(f"No existing API Gateway found")
            print(f"Run setup script to deploy infrastructure first:")
            print(f"   python scripts/setup.py --admin-user {config.load_deployment_config().get('admin_username', 'admin') if config.load_deployment_config() else 'admin'}")
            return False
        
        print(f"Service '{service_name}' added successfully!")
        print(f"API Endpoint: https://{existing_api}.execute-api.us-east-1.amazonaws.com/prod/credentials")
        print(f"Usage example:")
        print(f"   from universal_s3_library import UniversalS3Client")
        print(f"   client = UniversalS3Client('your-bucket', '{service_name}')")
        
        return True
        
    except Exception as e:
        print(f"Failed to add service: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Add service to Universal S3 Library')
    parser.add_argument('service_name', help='Service name (e.g., analytics, webapp)')
    parser.add_argument('bucket_patterns', help='Comma-separated bucket patterns (e.g., "app-*,*-data")')
    parser.add_argument('--permissions', choices=['read-only', 'read-write', 'admin'], 
                       default='read-write', help='Access level')
    parser.add_argument('--restricted-users', help='Comma-separated list of allowed users')
    parser.add_argument('--force', action='store_true', help='Overwrite existing service without confirmation')
    
    args = parser.parse_args()
    
    # Parse bucket patterns
    bucket_patterns = [p.strip() for p in args.bucket_patterns.split(',')]
    
    # Parse restricted users
    restricted_users = None
    if args.restricted_users:
        restricted_users = [u.strip() for u in args.restricted_users.split(',')]
    
    success = add_service(args.service_name, bucket_patterns, args.permissions, restricted_users, args.force)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())