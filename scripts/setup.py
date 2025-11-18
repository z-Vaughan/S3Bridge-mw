#!/usr/bin/env python3
"""
S3Bridge Midway Setup Script
Deploys infrastructure to any AWS account
"""

import boto3
import json
import time
import zipfile
import io
from pathlib import Path
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.aws_config import AWSConfig

def find_existing_api_gateway():
    """Find existing API Gateway that uses s3bridge-mw-credential-service"""
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
        print(f"⚠️  Could not search for existing API Gateway: {e}")
        return None

def create_lambda_zip(lambda_dir, function_name):
    """Create deployment zip for Lambda function"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        lambda_file = lambda_dir / f"{function_name}.py"
        if lambda_file.exists():
            zip_file.write(lambda_file, "lambda_function.py")
    
    return zip_buffer.getvalue()

def deploy_infrastructure(admin_username='admin', force=False):
    """Deploy S3Bridge Midway infrastructure"""
    
    config = AWSConfig()
    
    print(f"🚀 Deploying S3Bridge Midway to account {config.account_id}")
    print(f"📍 Region: {config.region}")
    print(f"👤 Admin user: {admin_username}")
    
    # Check for existing API Gateway first
    existing_api = find_existing_api_gateway()
    if existing_api:
        print(f"🔍 Found existing API Gateway: {existing_api}")
        if not force:
            print("⚠️  Infrastructure already deployed. Use --force to redeploy.")
            # Save configuration with existing API
            api_url = f"https://{existing_api}.execute-api.us-east-1.amazonaws.com/prod/credentials"
            config.save_deployment_config(api_url, admin_username)
            print(f"💾 Saved existing configuration")
            print(f"🔗 API URL: {api_url}")
            return True
    
    # Check if CloudFormation stack already deployed
    if config.is_deployed() and not force:
        print("⚠️  CloudFormation stack already deployed. Use --force to redeploy.")
        return False
    
    # Load CloudFormation template
    template_path = Path(__file__).parent.parent / "templates" / "infrastructure.yaml"
    with open(template_path) as f:
        template = f.read()
    
    # Deploy CloudFormation stack
    cf = boto3.client('cloudformation')
    
    try:
        print("📦 Creating CloudFormation stack...")
        cf.create_stack(
            StackName=config.stack_name,
            TemplateBody=template,
            Parameters=[
                {'ParameterKey': 'AdminUsername', 'ParameterValue': admin_username}
            ],
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        
        print("⏳ Waiting for stack creation...")
        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(StackName=config.stack_name, WaiterConfig={'Delay': 10, 'MaxAttempts': 60})
        
        print("✅ CloudFormation stack created successfully")
        
        # Deploy Lambda functions
        deploy_lambda_functions(config)
        
        # Get API Gateway URL
        api_url = config.get_api_gateway_url()
        
        # Save configuration
        config.save_deployment_config(api_url, admin_username)
        
        print(f"🎉 S3Bridge Midway deployed successfully!")
        print(f"🔗 API URL: {api_url}")
        print(f"📝 Next steps:")
        print(f"   1. Add services: s3bridge-mw add myapp 'myapp-*'")
        print(f"   2. Use in code: from s3bridge_mw import S3BridgeClient")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

def deploy_lambda_functions(config):
    """Deploy Lambda function code"""
    
    lambda_client = boto3.client('lambda')
    lambda_dir = Path(__file__).parent.parent / "lambda_functions"
    
    functions = [
        ('s3bridge_mw_credential_service', 's3bridge-mw-credential-service'),
        ('s3bridge_mw_midway_authorizer', 's3bridge-mw-authorizer')
    ]
    
    for file_name, function_name in functions:
        print(f"📤 Deploying {function_name}...")
        
        # Create deployment package
        zip_content = create_lambda_zip(lambda_dir, file_name)
        
        # Update function code
        try:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"✅ {function_name} deployed")
        except Exception as e:
            print(f"⚠️  Failed to deploy {function_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Deploy S3Bridge Midway')
    parser.add_argument('--admin-user', default='admin', 
                       help='Username for universal service access')
    parser.add_argument('--force', action='store_true',
                       help='Force redeploy if already exists')
    
    args = parser.parse_args()
    
    # Remove global variable approach
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("💡 Run 'aws configure' to set up credentials")
        return 1
    
    success = deploy_infrastructure(args.admin_user, args.force)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())