# Universal S3 Library

A modular, account-agnostic credential service for secure S3 access across multiple applications and AWS accounts.

## Quick Start

```bash
# Install
pip install universal-s3-library

# Setup infrastructure (one-time per AWS account)
python -m universal_s3_library.setup --admin-user myusername

# Add services
python -m universal_s3_library.add_service analytics "company-analytics-*" --permissions read-only
python -m universal_s3_library.add_service app1 "app1-data-*" --permissions read-write
```

```python
from universal_s3_library import UniversalS3Client

# Use with any AWS account
s3_client = UniversalS3Client("your-bucket-name", "analytics")
data = {"config": "value"}
s3_client.write_json(data, "config/settings.json")
```

## Features

- **Account Agnostic**: Works with any AWS account
- **One-Command Setup**: CloudFormation deployment
- **Dynamic Service Onboarding**: Add services via script
- **Midway Authentication**: Automatic cookie management
- **Multi-Tier Security**: Service-based access control

## Installation

### Prerequisites
- AWS CLI configured with admin permissions
- Python 3.9+
- Midway authentication (for Amazon internal use)

### Setup
```bash
# 1. Clone or download the library
git clone <repository-url> universal_s3_library
cd universal_s3_library

# 2. Install dependencies
pip install -r requirements.txt

# 3. Deploy infrastructure to your AWS account
python scripts/setup.py --admin-user your-username

# 4. Add your first service
python scripts/add_service.py myapp "myapp-*" --permissions read-write
```

**Smart Setup**: The setup script automatically:
- Detects existing API Gateway endpoints
- Reuses existing infrastructure when possible
- Only creates new resources when necessary

## Service Management

### Add New Service
```bash
# Python
python scripts/add_service.py SERVICE_NAME BUCKET_PATTERNS [OPTIONS]

# PowerShell (Windows)
.\add_service.ps1 -ServiceName SERVICE_NAME -BucketPatterns BUCKET_PATTERNS -Permissions PERMISSION_LEVEL

# Examples:
python scripts/add_service.py analytics "company-analytics-*,*-analytics-*" --permissions read-only
.\add_service.ps1 -ServiceName webapp -BucketPatterns "webapp-prod-*" -Permissions read-write
python scripts/add_service.py admin "*" --permissions admin --restricted-users admin,devops
```

**Smart Deployment**: The add_service script automatically:
- Detects existing API Gateway endpoints
- Updates only Lambda functions (preserves existing infrastructure)
- Avoids deployment loops and duplicate API creation

### Valid Permissions
- `read-only`: GetObject, ListBucket
- `read-write`: GetObject, PutObject, DeleteObject, ListBucket (default)
- `admin`: Full S3 access (s3:*)

## Usage Examples

```python
from universal_s3_library import UniversalS3Client

# Analytics service (read-only)
analytics = UniversalS3Client("company-analytics-data", "analytics")
reports = analytics.list_objects("reports/")

# Application service (read-write)
app = UniversalS3Client("webapp-prod-uploads", "webapp")
app.write_json({"user": "data"}, "users/user123.json")

# Admin service (full access, restricted users)
admin = UniversalS3Client("any-bucket", "admin")  # Only works for authorized users
admin.upload_file("backup.zip", "backups/daily.zip")
```

## Architecture

- **Lambda Functions**: Credential service + Midway authorizer
- **API Gateway**: Secure credential endpoint
- **IAM Roles**: Service-specific least-privilege roles
- **CloudFormation**: Infrastructure as code
- **Dynamic Configuration**: Account-aware service mapping

## Documentation

- [Setup Guide](docs/SETUP.md)
- [Service Management](docs/SERVICES.md)
- [API Reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)