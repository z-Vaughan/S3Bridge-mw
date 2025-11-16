#!/usr/bin/env pwsh
# Quick service addition for Universal S3 Library

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName,
    
    [Parameter(Mandatory=$true)]
    [string]$BucketPatterns,
    
    [ValidateSet("read-only", "read-write", "admin")]
    [string]$Permissions = "read-write",
    
    [string]$RestrictedUsers
)

Write-Host "Universal S3 Library - Add Service" -ForegroundColor Cyan

# Build command
$cmd = "python scripts/add_service.py `"$ServiceName`" `"$BucketPatterns`" --permissions $Permissions"

if ($RestrictedUsers) {
    $cmd += " --restricted-users `"$RestrictedUsers`""
}

# Execute
Invoke-Expression $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nService '$ServiceName' ready for use!" -ForegroundColor Green
}