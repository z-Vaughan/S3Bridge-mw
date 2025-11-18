import json
import boto3
import os
from datetime import datetime

def get_service_config():
    """Load service configuration from environment variables"""
    
    services = {}
    
    # Add universal service if admin username is set
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    if admin_username:
        services['universal'] = {
            'role': f"arn:aws:iam::{os.environ['AWS_ACCOUNT_ID']}:role/service-role/universal-s3-access-role",
            'buckets': ['*'],
            'restricted_users': [admin_username]
        }
    
    # Load services from environment variables
    for key, value in os.environ.items():
        if key.startswith('SERVICE_'):
            service_name = key[8:].lower()  # Remove 'SERVICE_' prefix
            try:
                services[service_name] = json.loads(value)
            except json.JSONDecodeError:
                continue
    
    return services

def lambda_handler(event, context):
    """
    S3Bridge Midway credential service - returns temporary AWS credentials for registered services
    """
    
    try:
        # Extract parameters
        params = event.get('queryStringParameters') or {}
        service_name = params.get('service')
        duration = int(params.get('duration', '3600'))
        
        if not service_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'service parameter required'})
            }
        
        # Load service configuration
        service_roles = get_service_config()
        service_config = service_roles.get(service_name)
        
        if not service_config:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown service: {service_name}'})
            }
        
        # Extract user ID from request context (set by midway authorizer)
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = authorizer_context.get('userId') or authorizer_context.get('principalId', 'unknown')
        
        # Check user restrictions for service
        if 'restricted_users' in service_config:
            if user_id not in service_config['restricted_users']:
                return {
                    'statusCode': 403,
                    'body': json.dumps({'error': f'User {user_id} not authorized for service {service_name}'})
                }
        
        role_arn = service_config['role']
        
        # Assume role
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"{service_name}-session-{int(datetime.now().timestamp())}",
            DurationSeconds=min(duration, 3600)
        )
        
        credentials = response['Credentials']
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'AccessKeyId': credentials['AccessKeyId'],
                'SecretAccessKey': credentials['SecretAccessKey'],
                'SessionToken': credentials['SessionToken'],
                'Expiration': credentials['Expiration'].isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }