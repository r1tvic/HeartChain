"""
Configuration module for HeartChain Backend.
Loads environment variables and provides typed configuration.
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "heartchain_db"
    
    # Encryption - AES-256-GCM requires a 32-byte key (256 bits)
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    ENCRYPTION_KEY: str = ""
    
    # IPFS Configuration
    IPFS_API_URL: str = "http://localhost:5001"
    IPFS_GATEWAY_URL: str = "http://localhost:8080/ipfs"
    
    # File Upload Settings
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list = [
        "application/pdf", 
        "image/jpeg", 
        "image/png", 
        "image/jpg",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    
    # Admin
    ADMIN_PASSWORD: str = "secret"
    
    # Blockchain
    SHARDEUM_RPC_URL: str = "https://liberty10.shardeum.org/" # Example Testnet
    CONTRACT_ADDRESS: str = "0x0000000000000000000000000000000000000000" # TO BE DEPLOYED
    ADMIN_PRIVATE_KEY: str = "0x0000000000000000000000000000000000000000000000000000000000000000" # Placeholder
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
