"""
S3Bridge Midway
Account-agnostic credential service for secure S3 access with Midway authentication
"""

from .s3bridge_client import S3BridgeClient
from .s3bridge_auth import S3BridgeAuthProvider

__version__ = "1.0.0"
__all__ = ["S3BridgeClient", "S3BridgeAuthProvider"]