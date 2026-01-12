from fastapi import APIRouter, HTTPException
from models.campaign import EncryptedField
from core.encryption import get_encryption

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/decrypt")
def decrypt_field(field: EncryptedField):
    """
    Helper to decrypt data (Admin only).
    Ideally protected by Admin Private Key signature or Auth.
    """
    try:
        encryption = get_encryption()
        # encryption.decrypt expects dict with nonce/ciphertext
        return {"decrypted": encryption.decrypt(field.model_dump())}
    except Exception as e:
        raise HTTPException(400, detail=f"Decryption failed: {e}")
