# S3Bridge Midway Service Management

## Service Configuration

Services in S3Bridge Midway are configured with:
- **Bucket Patterns**: S3 bucket access patterns (wildcards supported)
- **Permissions**: Access level (read-only, read-write, admin)
- **User Restrictions**: Midway users allowed to access the service

## Adding Services

### Basic Service
```bash
s3bridge-mw add myservice "myservice-*" --permissions read-write
```

### Service with User Restrictions
```bash
s3bridge-mw add analytics "analytics-*,reports-*" --permissions read-only --restricted-users analyst1,analyst2,manager1
```

### Service Parameters

- `service_name`: Unique identifier for the service
- `bucket_patterns`: Comma-separated S3 bucket patterns
- `--permissions`: Access level (read-only, read-write, admin)
- `--restricted-users`: Comma-separated list of allowed Midway users
- `--force`: Overwrite existing service without confirmation

## Listing Services

```bash
s3bridge-mw list
```

Output shows:
- Service name
- IAM role ARN
- Bucket patterns
- Restricted users (if any)
- Service status

## Editing Services

### Update Bucket Patterns
```bash
s3bridge-mw edit myservice --bucket-patterns "myservice-*,shared-*"
```

### Update User Restrictions
```bash
s3bridge-mw edit analytics --restricted-users user1,user2,user3,newuser
```

### Update Permissions
```bash
s3bridge-mw edit myservice --permissions admin
```

### Remove User Restrictions
```bash
s3bridge-mw edit myservice --restricted-users ""
```

## Removing Services

```bash
# With confirmation
s3bridge-mw remove oldservice

# Skip confirmation
s3bridge-mw remove oldservice --force
```

This removes:
- Service configuration from Lambda environment
- IAM role and policies
- All associated permissions

## Permission Levels

### read-only
- `s3:GetObject`: Download objects
- `s3:ListBucket`: List bucket contents

### read-write (default)
- `s3:GetObject`: Download objects
- `s3:PutObject`: Upload objects
- `s3:DeleteObject`: Delete objects
- `s3:ListBucket`: List bucket contents

### admin
- `s3:*`: Full S3 access to matched buckets

## User Restrictions

### Behavior
- If `restricted_users` is specified, only those users can access the service
- If not specified, all authenticated Midway users can access the service
- Universal service is always restricted to admin user only

### User Validation
- Users are validated via Midway authentication
- User ID is extracted from Midway cookie
- Access denied if user not in restricted list

### Examples

```bash
# Restrict to specific team
s3bridge-mw add teamservice "team-*" --restricted-users alice,bob,charlie

# Analytics team access
s3bridge-mw add analytics "analytics-*" --permissions read-only --restricted-users analyst1,analyst2,manager

# Admin-only service
s3bridge-mw add admin-service "*" --permissions admin --restricted-users admin
```

## Bucket Pattern Matching

### Wildcards
- `*`: Matches any characters
- `myapp-*`: Matches myapp-dev, myapp-prod, etc.
- `*-data`: Matches analytics-data, user-data, etc.

### Multiple Patterns
```bash
s3bridge-mw add webapp "webapp-*,shared-assets,cdn-*" --permissions read-write
```

### Exact Names
```bash
s3bridge-mw add specific "exact-bucket-name" --permissions read-only
```

## Service Status

Services can have different statuses:
- **Active**: Both IAM role and Lambda configuration exist
- **Missing IAM role**: Configuration exists but IAM role missing
- **Missing Lambda config**: IAM role exists but Lambda configuration missing
- **Inactive**: Neither configuration nor role exists