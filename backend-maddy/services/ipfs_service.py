import hashlib
import json
from pathlib import Path
import httpx
from core.config import settings

# Mock IPFS Configuration
MOCK_IPFS_DIR = Path("mock_ipfs")
MOCK_IPFS_DIR.mkdir(exist_ok=True)

async def save_to_mock_ipfs(content: bytes) -> str:
    """Save content to local mock directory when IPFS is down."""
    sha256 = hashlib.sha256(content).hexdigest()
    fake_cid = f"QmMOCK{sha256[:40]}" 
    
    file_path = MOCK_IPFS_DIR / fake_cid
    with open(file_path, "wb") as f:
        f.write(content)
        
    return fake_cid

async def get_from_mock_ipfs(cid: str) -> bytes:
    """Retrieve from local mock storage."""
    file_path = MOCK_IPFS_DIR / cid
    if file_path.exists():
        with open(file_path, "rb") as f:
            return f.read()
    raise FileNotFoundError(f"File {cid} not found in Mock storage")

async def upload_bytes(content: bytes) -> str:
    """
    Upload raw bytes to IPFS (or Mock).
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"{settings.IPFS_API_URL}/api/v0/add"
            files = {"file": ("file", content)}
            
            # Short timeout to fail fast and use Mock
            response = await client.post(url, files=files, timeout=2.0)
            
            if response.status_code != 200:
                print(f"IPFS Error {response.status_code}. Using Mock.")
                return await save_to_mock_ipfs(content)
            
            result = response.json()
            return result["Hash"]
            
    except (httpx.RequestError, httpx.TimeoutException):
        print("IPFS Unreachable. Using Mock.")
        return await save_to_mock_ipfs(content)

async def upload_json(data: dict) -> str:
    """
    Upload a JSON object to IPFS (or Mock).
    Used for Campaign Metadata.
    """
    content = json.dumps(data, default=str).encode('utf-8')
    return await upload_bytes(content)

async def retrieve_json(cid: str) -> dict:
    """
    Retrieve and parse JSON from IPFS (or Mock).
    """
    if cid.startswith("QmMOCK"):
        content = await get_from_mock_ipfs(cid)
    else:
        # Real IPFS fetch
        try:
            async with httpx.AsyncClient() as client:
                url = f"{settings.IPFS_GATEWAY_URL}/{cid}"
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    raise Exception(f"IPFS Gateway Error: {response.status_code}")
                content = response.content
        except Exception:
            # Fallback to mock checks?
            try:
                content = await get_from_mock_ipfs(cid)
            except:
                raise Exception("Could not retrieve file from IPFS or Mock")
    
    return json.loads(content)
