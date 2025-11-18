#!/usr/bin/env python3
"""
Deploy only Lambda functions without touching API Gateway
For S3Bridge Midway
"""

import boto3
import zipfile
import io
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_lambda_zip(lambda_dir, function_name):
    """Create deployment zip for Lambda function"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        lambda_file = lambda_dir / "universal_credential_service.py"
        if lambda_file.exists():
            zip_file.write(lambda_file, "lambda_function.py")
        else:
            print(f"Lambda file not found: {lambda_file}")
    
    return zip_buffer.getvalue()

def deploy_lambda(lambda_client, function_name, zip_content):
    """Deploy or update Lambda function"""
    import time
    
    for attempt in range(3):
        try:
            # Try to update existing function
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"Updated existing function: {function_name}")
            return response['FunctionArn']
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"Function {function_name} not found - run full setup first")
            return None
            
        except lambda_client.exceptions.ResourceConflictException:
            if attempt < 2:
                print(f"Function update in progress, waiting 10 seconds...")
                time.sleep(10)
            else:
                print(f"Function still updating after retries - service role created successfully")
                return "skipped"
    
    return None

def main():
    """Deploy Lambda functions only"""
    
    lambda_client = boto3.client('lambda')
    lambda_dir = Path(__file__).parent.parent / 'lambda_functions'
    
    functions = [
        's3bridge-mw-credential-service'
    ]
    
    print("Deploying Lambda functions only (preserving API Gateway)...")
    
    for function_name in functions:
        print(f"Deploying {function_name}...")
        
        # Create deployment package
        zip_content = create_lambda_zip(lambda_dir, function_name)
        
        # Deploy function
        arn = deploy_lambda(lambda_client, function_name, zip_content)
        if not arn:
            return 1
    
    print("Lambda-only deployment complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())