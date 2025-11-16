"""
Universal S3 Library
Account-agnostic credential service for secure S3 access
"""

from .universal_s3_client import UniversalS3Client
from .universal_auth import UniversalAuthProvider

__version__ = "1.0.0"
__all__ = ["UniversalS3Client", "UniversalAuthProvider"]