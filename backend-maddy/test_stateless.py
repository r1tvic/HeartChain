import requests
import json

data = {
    "title": "Decentralized Campaign",
    "description": "This campaign's metadata is stored on IPFS and validated via Shardeum.",
    "target_amount": 1000,
    "duration_days": 30,
    "category": "Technology",
    "priority": "normal",
    "beneficiary_name": "Jane Doe",
    "phone_number": "1234567890",
    "residential_address": "123 Web3 Lane",
    "documents": []
}

try:
    print("Sending create request...")
    response = requests.post("http://localhost:8000/campaigns/individual", json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("Success!")
        print(json.dumps(response.json(), indent=2))
        
        # Verify IPFS CID is returned
        cid = response.json().get("cid")
        if cid:
            print(f"Metadata uploaded to IPFS CID: {cid}")
    else:
        print("Failed")
        print(response.text)

except Exception as e:
    print(f"Error: {e}")
