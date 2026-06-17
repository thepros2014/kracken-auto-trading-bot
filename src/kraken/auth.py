"""
Kraken Authentication Module
Handles API key management and request signing
"""
import hashlib
import hmac
import base64
import urllib.parse
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class KrakenAuth:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def _get_nonce(self) -> str:
        """Generate a nonce for API requests"""
        return str(int(time.time() * 1000))
    
    def _sign_message(self, urlpath: str, data: Dict) -> str:
        """Sign a message for Kraken API authentication"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        secret = base64.b64decode(self.api_secret)
        signature = hmac.new(secret, message, hashlib.sha512)
        sigdigest = base64.b64encode(signature.digest())
        
        return sigdigest.decode()
    
    def get_headers(self, urlpath: str, data: Dict) -> Dict[str, str]:
        """Get authentication headers for Kraken API"""
        data['nonce'] = self._get_nonce()
        signature = self._sign_message(urlpath, data)
        
        return {
            'API-Key': self.api_key,
            'API-Sign': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

# Utility functions for API key validation
def validate_api_credentials(api_key: str, api_secret: str) -> bool:
    """Validate that API credentials are properly formatted"""
    if not api_key or not api_secret:
        return False
    
    # Basic format checks
    if len(api_key) < 10 or len(api_secret) < 10:
        return False
    
    return True

def mask_api_key(api_key: str) -> str:
    """Mask API key for logging/display purposes"""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]