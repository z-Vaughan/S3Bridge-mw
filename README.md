# S3Bridge Midway

A modular, account-agnostic credential service for secure S3 access across multiple applications and AWS accounts with Midway authentication.

## Quick Start

```bash
# Install
pip install s3bridge-mw

# Setup infrastructure (one-time per AWS account)
python -m s3bridge-mw.setup --admin-user myusername

# Add services with user restrictions
s3bridge-mw add analytics "company-analytics-*" --permissions read-only --restricted-users user1,user2
s3bridge-mw add app1 "app1-data-*" --permissions read-write --restricted-users user3
```

```python
from s3bridge_mw import S3BridgeClient

# Use with any AWS account (requires Midway authentication)
s3_client = S3BridgeClient("your-bucket-name", "analytics")
data = {"config": "value"}
s3_client.write_json(data, "config/settings.json")
```

## Features

- **Account Agnostic**: Works with any AWS account
- **Midway Authentication**: Cookie-based authentication via Midway
- **User Restrictions**: Service-level user access control
- **One-Command Setup**: CloudFormation deployment
- **Dynamic Service Onboarding**: Add services via script
- **Multi-Tier Security**: Service-based access control

## Installation

### Prerequisites
- AWS CLI configured with admin permissions
- Python 3.9+
- Midway authentication setup

### Setup
```bash
# 1. Clone or download the library
git clone <repository-url> s3bridge-mw
cd s3bridge-mw

# 2. Install dependencies
pip install -r requirements.txt

# 3. Deploy infrastructure to your AWS account
s3bridge-mw setup --admin-user your-username

# 4. Add your first service with user restrictions
s3bridge-mw add myapp "myapp-*" --permissions read-write --restricted-users user1,user2
```

**Smart Setup**: The setup script automatically:
- Detects existing API Gateway endpoints
- Reuses existing infrastructure when possible
- Only creates new resources when necessary
- Configures Midway authorizer for authentication

## Service Management

### Unified Service Manager
```bash
# List all services
s3bridge-mw list

# Add new service with user restrictions
s3bridge-mw add myapp "myapp-*" --permissions read-write --restricted-users user1,user2

# Edit existing service
s3bridge-mw edit myapp --bucket-patterns "myapp-*,shared-*" --restricted-users user1,user2,user3

# Remove service
s3bridge-mw remove myapp --force

# Show system status
s3bridge-mw status
```

### Valid Permissions
- `read-only`: GetObject, ListBucket
- `read-write`: GetObject, PutObject, DeleteObject, ListBucket (default)
- `admin`: Full S3 access (s3:*)

### User Restrictions
- `--restricted-users`: Comma-separated list of Midway users allowed to access the service
- If not specified, service is accessible to all authenticated users
- Universal service is restricted to admin user only

## Usage Examples

```python
from s3bridge_mw import S3BridgeClient

# Analytics service (read-only, restricted users)
analytics = S3BridgeClient("company-analytics-data", "analytics")
reports = analytics.list_objects("reports/")

# Application service (read-write, specific users)
app = S3BridgeClient("webapp-prod-uploads", "webapp")
app.write_json({"user": "data"}, "users/user123.json")

# Admin service (full access, admin only)
admin = S3BridgeClient("any-bucket", "universal")
admin.upload_file("backup.zip", "backups/daily.zip")
```

## Architecture

- **Lambda Functions**: Credential service with Midway authentication
- **API Gateway**: Secure credential endpoint with custom authorizer
- **Midway Authorizer**: Cookie-based user authentication
- **IAM Roles**: Service-specific least-privilege roles
- **CloudFormation**: Infrastructure as code
- **Dynamic Configuration**: Account-aware service mapping with user restrictions

## Authentication Flow

1. User authenticates via Midway (cookie-based)
2. API Gateway custom authorizer validates Midway cookie
3. Service checks user restrictions for requested service
4. Temporary AWS credentials returned if authorized

## Differences from Standard S3Bridge

- **Authentication**: Midway cookies instead of API keys
- **User Restrictions**: Service-level user access control
- **Resource Names**: Prefixed with `s3bridge-mw` to avoid conflicts
- **CLI Command**: `s3bridge-mw` instead of `s3bridge`

## Documentation

- [Setup Guide](docs/SETUP.md)
- [Service Management](docs/SERVICES.md)
- [API Reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)