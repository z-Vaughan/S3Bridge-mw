# S3Bridge Midway Setup Guide

## Prerequisites

- AWS CLI configured with administrative permissions
- Python 3.9 or higher
- Midway authentication environment

## Installation

```bash
pip install s3bridge-mw
```

## Infrastructure Deployment

### Initial Setup

```bash
# Deploy infrastructure to your AWS account
s3bridge-mw setup --admin-user your-midway-username
```

This creates:
- CloudFormation stack: `s3bridge-mw`
- Lambda function: `s3bridge-mw-credential-service`
- Lambda authorizer: `s3bridge-mw-authorizer`
- API Gateway: `s3bridge-mw`
- IAM role: `s3bridge-mw-lambda-role`

### Verification

```bash
# Check deployment status
aws cloudformation describe-stacks --stack-name s3bridge-mw

# Verify Lambda functions
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 's3bridge-mw')]"
```

## Service Configuration

### Adding Services

```bash
# Basic service
s3bridge-mw add myapp "myapp-*" --permissions read-write

# Service with user restrictions
s3bridge-mw add analytics "analytics-*" --permissions read-only --restricted-users user1,user2,user3

# Service with multiple bucket patterns
s3bridge-mw add webapp "webapp-*,shared-data-*" --permissions read-write --restricted-users webteam
```

### Managing Services

```bash
# List all services
s3bridge-mw list

# Edit service restrictions
s3bridge-mw edit analytics --restricted-users user1,user2,user3,user4

# Remove service
s3bridge-mw remove oldservice --force
```

## Authentication Setup

### Midway Integration

The system uses Midway cookies for authentication:

1. Users must be authenticated via Midway
2. API Gateway custom authorizer validates cookies
3. Service-level user restrictions are enforced

### User Restrictions

- Services can be restricted to specific Midway users
- Universal service is restricted to admin user only
- Unrestricted services are accessible to all authenticated users

## Troubleshooting

### Common Issues

**Stack already exists:**
```bash
s3bridge-mw setup --admin-user myuser --force
```

**Lambda deployment fails:**
```bash
# Check function status
aws lambda get-function --function-name s3bridge-mw-credential-service
```

**Service not found:**
```bash
# Verify service exists
s3bridge-mw list
```

### Resource Conflicts

S3Bridge Midway uses prefixed resource names to avoid conflicts with standard S3Bridge:
- All resources prefixed with `s3bridge-mw`
- Separate CloudFormation stack
- Independent service configurations