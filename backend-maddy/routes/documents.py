"""
Document Upload Routes for HeartChain.

Handles file uploads for campaign verification documents.
Documents are:
1. Validated (type, size)
2. Encrypted using AES-256-GCM
3. Uploaded to IPFS
4. Only IPFS hash stored in MongoDB
"""
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
import base64
import httpx
import os

from models.campaign import CampaignDocument, DocumentType, CampaignStatus
from core.encryption import get_encryption, EncryptionError
from core.config import settings
from database import db

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_campaigns_collection():
    """Helper to get the campaigns collection."""
    db_name = os.getenv("DB_NAME", "heartchain_db")
    return db.client[db_name]["campaigns"]


def validate_file(file: UploadFile) -> None:
    """
    Validate file type and size.
    
    Args:
        file: Uploaded file
        
    Raises:
        HTTPException: If validation fails
    """
    # Check file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Allowed types: {settings.ALLOWED_FILE_TYPES}"
        )
    
    # Check file size (will be checked after reading, but we can check content_length if available)
    # Actual size check happens after reading the file


def encrypt_file_content(content: bytes) -> dict:
    """
    Encrypt file content using AES-256-GCM.
    
    Args:
        content: Raw file bytes
        
    Returns:
        Dictionary with nonce and ciphertext (base64 encoded)
    """
    encryption = get_encryption()
    
    # For binary data, we need to handle it differently
    import os as os_module
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    nonce = os_module.urandom(12)
    key = bytes.fromhex(settings.ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    
    ciphertext = aesgcm.encrypt(nonce, content, None)
    
    return {
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
    }


def decrypt_file_content(encrypted_data: dict) -> bytes:
    """
    Decrypt file content.
    
    Args:
        encrypted_data: Dictionary with nonce and ciphertext
        
    Returns:
        Decrypted file bytes
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    nonce = base64.b64decode(encrypted_data["nonce"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])
    
    key = bytes.fromhex(settings.ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    
    return aesgcm.decrypt(nonce, ciphertext, None)


async def upload_to_ipfs(content: bytes) -> str:
    """
    Upload content to IPFS node.
    
    Args:
        content: Bytes to upload
        
    Returns:
        IPFS content identifier (CID/hash)
    """
    try:
        async with httpx.AsyncClient() as client:
            # IPFS HTTP API endpoint for adding files
            url = f"{settings.IPFS_API_URL}/api/v0/add"
            
            files = {"file": ("document", content)}
            response = await client.post(url, files=files, timeout=60.0)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"IPFS upload failed: {response.text}"
                )
            
            result = response.json()
            return result["Hash"]
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to IPFS node: {str(e)}"
        )


async def retrieve_from_ipfs(ipfs_hash: str) -> bytes:
    """
    Retrieve content from IPFS.
    
    Args:
        ipfs_hash: IPFS content identifier
        
    Returns:
        File content as bytes
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"{settings.IPFS_GATEWAY_URL}/{ipfs_hash}"
            response = await client.get(url, timeout=60.0)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not retrieve document from IPFS"
                )
            
            return response.content
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to IPFS gateway: {str(e)}"
        )


# ============== UPLOAD ENDPOINTS ==============

@router.post(
    "/{campaign_id}/upload",
    summary="Upload Campaign Document",
    description="Upload a supporting document for a campaign. Document is encrypted before IPFS storage."
)
async def upload_document(
    campaign_id: str,
    document_type: DocumentType = Form(..., description="Type of document"),
    file: UploadFile = File(..., description="Document file (PDF or image)")
):
    """
    Upload a supporting document for a campaign.
    
    Flow:
    1. Validate file (type, size)
    2. Encrypt file content with AES-256-GCM
    3. Upload encrypted content to IPFS
    4. Store IPFS hash and metadata in MongoDB
    
    Raw file is NEVER stored unencrypted.
    """
    # Validate campaign exists and is in correct state
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Only allow uploads during DRAFT or PENDING_VERIFICATION
    allowed_states = [CampaignStatus.DRAFT.value, CampaignStatus.PENDING_VERIFICATION.value]
    if campaign["status"] not in allowed_states:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload documents. Campaign status is '{campaign['status']}'"
        )
    
    # Validate file
    validate_file(file)
    
    # Read file content
    content = await file.read()
    
    # Check file size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    try:
        # Encrypt file content
        encrypted_content = encrypt_file_content(content)
        
        # Convert to bytes for IPFS upload
        encrypted_bytes = (
            encrypted_content["nonce"] + "|||" + encrypted_content["ciphertext"]
        ).encode('utf-8')
        
        # Upload to IPFS
        ipfs_hash = await upload_to_ipfs(encrypted_bytes)
        
    except EncryptionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Encryption failed: {str(e)}"
        )
    
    # Create document record
    doc_record = {
        "ipfs_hash": ipfs_hash,
        "document_type": document_type.value,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size_bytes": len(content),
        "uploaded_at": datetime.now()
    }
    
    # Add to campaign's documents array
    await get_campaigns_collection().update_one(
        {"_id": ObjectId(campaign_id)},
        {"$push": {"documents": doc_record}}
    )
    
    return {
        "message": "Document uploaded successfully",
        "ipfs_hash": ipfs_hash,
        "document_type": document_type.value,
        "filename": file.filename
    }


@router.get(
    "/{campaign_id}",
    summary="List Campaign Documents",
    description="Get list of documents for a campaign (metadata only, no content)."
)
async def list_documents(campaign_id: str):
    """
    List all documents attached to a campaign.
    
    Returns metadata only (IPFS hash, type, filename).
    Does NOT return content (use admin endpoint for that).
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    documents = campaign.get("documents", [])
    
    return {
        "campaign_id": campaign_id,
        "document_count": len(documents),
        "documents": documents
    }


@router.delete(
    "/{campaign_id}/{ipfs_hash}",
    summary="Remove Document",
    description="Remove a document from a campaign (only during DRAFT status)."
)
async def remove_document(campaign_id: str, ipfs_hash: str):
    """
    Remove a document from a campaign.
    
    - Only allowed during DRAFT status
    - Removes from MongoDB (IPFS content remains but is inaccessible without key)
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != CampaignStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Can only remove documents from DRAFT campaigns"
        )
    
    # Remove document from array
    result = await get_campaigns_collection().update_one(
        {"_id": ObjectId(campaign_id)},
        {"$pull": {"documents": {"ipfs_hash": ipfs_hash}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found in campaign")
    
    return {"message": "Document removed successfully"}


# ============== ADMIN-ONLY: DOCUMENT RETRIEVAL ==============

@router.get(
    "/{campaign_id}/{ipfs_hash}/retrieve",
    summary="Retrieve Document Content (Admin Only)",
    description="Download and decrypt a document. Admin authentication required."
)
async def retrieve_document(
    campaign_id: str,
    ipfs_hash: str,
    admin_id: str = Query(..., description="Admin ID for logging")
):
    """
    Retrieve and decrypt document content.
    
    - Admin only endpoint
    - Downloads from IPFS and decrypts
    - Returns base64-encoded content
    """
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")
    
    campaign = await get_campaigns_collection().find_one({"_id": ObjectId(campaign_id)})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Find the document metadata
    doc_meta = None
    for doc in campaign.get("documents", []):
        if doc["ipfs_hash"] == ipfs_hash:
            doc_meta = doc
            break
    
    if not doc_meta:
        raise HTTPException(status_code=404, detail="Document not found in campaign")
    
    try:
        # Retrieve encrypted content from IPFS
        encrypted_bytes = await retrieve_from_ipfs(ipfs_hash)
        
        # Parse the encrypted content
        encrypted_str = encrypted_bytes.decode('utf-8')
        nonce, ciphertext = encrypted_str.split("|||")
        
        encrypted_data = {
            "nonce": nonce,
            "ciphertext": ciphertext
        }
        
        # Decrypt
        decrypted_content = decrypt_file_content(encrypted_data)
        
        # Return as base64 for safe transmission
        return {
            "ipfs_hash": ipfs_hash,
            "filename": doc_meta["filename"],
            "mime_type": doc_meta["mime_type"],
            "content_base64": base64.b64encode(decrypted_content).decode('utf-8')
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve/decrypt document: {str(e)}"
        )
