"""
AES-256-GCM Encryption Module for HeartChain.

This module provides application-level encryption for sensitive data
before storing in MongoDB. Uses authenticated encryption for both
confidentiality and integrity.
"""
import os
import base64
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from core.config import settings


class EncryptionError(Exception):
    """Custom exception for encryption-related errors."""
    pass


class DecryptionError(Exception):
    """Custom exception for decryption-related errors."""
    pass


class AESEncryption:
    """
    AES-256-GCM encryption handler.
    
    Uses:
    - 256-bit key (32 bytes)
    - 96-bit nonce (12 bytes) - recommended for GCM
    - 128-bit authentication tag (built into GCM)
    """
    
    NONCE_SIZE = 12  # 96 bits - recommended for AES-GCM
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption with a hex-encoded key.
        
        Args:
            key: Hex-encoded 32-byte key. If None, uses ENCRYPTION_KEY from settings.
        """
        key_hex = key or settings.ENCRYPTION_KEY
        
        if not key_hex:
            raise EncryptionError(
                "Encryption key not configured. Set ENCRYPTION_KEY in environment variables. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        
        try:
            self._key = bytes.fromhex(key_hex)
            if len(self._key) != 32:
                raise EncryptionError(
                    f"Encryption key must be 32 bytes (64 hex characters). Got {len(self._key)} bytes."
                )
            self._aesgcm = AESGCM(self._key)
        except ValueError as e:
            raise EncryptionError(f"Invalid encryption key format: {e}")
    
    def encrypt(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt a string value using AES-256-GCM.
        
        Args:
            plaintext: The string to encrypt.
            
        Returns:
            Dictionary with 'nonce' and 'ciphertext' (both base64-encoded).
        """
        if not plaintext:
            return {"nonce": "", "ciphertext": ""}
        
        try:
            # Generate a random nonce for each encryption
            nonce = os.urandom(self.NONCE_SIZE)
            
            # Encrypt the plaintext
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self._aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # Return base64-encoded values for safe storage
            return {
                "nonce": base64.b64encode(nonce).decode('utf-8'),
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
            }
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt an encrypted value.
        
        Args:
            encrypted_data: Dictionary with 'nonce' and 'ciphertext' (base64-encoded).
            
        Returns:
            Decrypted plaintext string.
        """
        if not encrypted_data or not encrypted_data.get("ciphertext"):
            return ""
        
        try:
            nonce = base64.b64decode(encrypted_data["nonce"])
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            
            plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except InvalidTag:
            raise DecryptionError("Decryption failed: Invalid authentication tag. Data may be corrupted or tampered.")
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing fields to encrypt.
            fields_to_encrypt: List of field names to encrypt.
            
        Returns:
            New dictionary with specified fields encrypted.
        """
        result = data.copy()
        
        for field in fields_to_encrypt:
            if field in result and result[field] is not None:
                if isinstance(result[field], str):
                    result[field] = self.encrypt(result[field])
                # Skip if already encrypted (has nonce/ciphertext structure)
                elif isinstance(result[field], dict) and "nonce" in result[field]:
                    continue
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted fields.
            fields_to_decrypt: List of field names to decrypt.
            
        Returns:
            New dictionary with specified fields decrypted.
        """
        result = data.copy()
        
        for field in fields_to_decrypt:
            if field in result and result[field] is not None:
                if isinstance(result[field], dict) and "nonce" in result[field]:
                    result[field] = self.decrypt(result[field])
        
        return result


# Singleton instance for use across the application
_encryption_instance: Optional[AESEncryption] = None


def get_encryption() -> AESEncryption:
    """
    Get or create the encryption singleton.
    
    Returns:
        AESEncryption instance.
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = AESEncryption()
    return _encryption_instance


def encrypt_field(value: str) -> Dict[str, str]:
    """
    Convenience function to encrypt a single field.
    
    Args:
        value: String value to encrypt.
        
    Returns:
        Encrypted data dictionary.
    """
    return get_encryption().encrypt(value)


def decrypt_field(encrypted_data: Dict[str, str]) -> str:
    """
    Convenience function to decrypt a single field.
    
    Args:
        encrypted_data: Encrypted data dictionary.
        
    Returns:
        Decrypted string.
    """
    return get_encryption().decrypt(encrypted_data)
