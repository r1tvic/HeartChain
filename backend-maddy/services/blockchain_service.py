from web3 import Web3
from core.config import settings

# Minimal ABI for createCampaign
CONTRACT_ABI = [
    {
      "inputs": [
        {"internalType": "uint256", "name": "_goal", "type": "uint256"},
        {"internalType": "string", "name": "_metadataCID", "type": "string"}
      ],
      "name": "createCampaign",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    }
]

async def create_campaign_on_chain(goal_amount: float, metadata_cid: str) -> str:
    """
    Calls HeartChain.createCampaign(goal, cid) on Shardeum.
    Returns Transaction Hash.
    """
    # Check for placeholder config
    if "000000000" in settings.ADMIN_PRIVATE_KEY or "000000000" in settings.CONTRACT_ADDRESS:
        print(f"MOCK BLOCKCHAIN: Creating campaign with goal {goal_amount} and CID {metadata_cid}")
        return f"0xMOCK_TX_HASH_{metadata_cid[:8]}"

    try:
        w3 = Web3(Web3.HTTPProvider(settings.SHARDEUM_RPC_URL))
        
        if not w3.is_connected():
            print("ERROR: Could not connect to Shardeum RPC. Returning Mock Hash.")
            return f"0xMOCK_TX_FAIL_{metadata_cid[:8]}"
            
        account = w3.eth.account.from_key(settings.ADMIN_PRIVATE_KEY)
        contract = w3.eth.contract(address=settings.CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        
        # Convert float goal to Wei (assuming 18 decimals?)
        # For simplicity in MVP, let's treat goal as integer "Tokens" or "Wei"
        # If goal is 5000 (USD/Tokens), we pass 5000 * 10^18?
        # Let's assume input is standard units.
        goal_wei = w3.to_wei(goal_amount, 'ether')
        
        # Build Transaction
        tx = contract.functions.createCampaign(goal_wei, metadata_cid).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        # Sign
        signed_tx = w3.eth.account.sign_transaction(tx, settings.ADMIN_PRIVATE_KEY)
        
        # Send
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()
        
    except Exception as e:
        print(f"Blockchain Error: {e}")
        return f"0xERROR_TX_{metadata_cid[:8]}"
