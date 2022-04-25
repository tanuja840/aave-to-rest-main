# gas_station.py
# TODO: estimate gas before transactions??
# 
from eth_account.account import Account
from web3 import Web3

# Load Configs 
from pyaml_env import parse_config
CONFIGS = parse_config("./config.yaml")
NETWORK_CONFIGS = CONFIGS["networks"]

W3 = Web3(Web3.HTTPProvider(NETWORK_CONFIGS["rpc_url"]))

def top_up(user_wallet_address: str):
  print("At gas station...")

  try:
    gas_station_address = Web3.toChecksumAddress(CONFIGS["gas_station"]["address"])
    user_wallet_address = Web3.toChecksumAddress(user_wallet_address)
    nonce = W3.eth.getTransactionCount(gas_station_address)
    gas_station_account = Account.from_key(CONFIGS["gas_station"]["sk"])

    transaction = {
      "chainId": NETWORK_CONFIGS["chain_id"],
      "type": 2, #EIP-1559 dynamic fee
      "nonce": nonce,
      # 
      "to": user_wallet_address,
      "value": CONFIGS["gas_station"]["gas_allowance"], # in wei
      "data": "",
      # Gas fees
      "gas": NETWORK_CONFIGS["default_gas_units"],
      "maxFeePerGas": NETWORK_CONFIGS["gas_price"],
      "maxPriorityFeePerGas": NETWORK_CONFIGS["miner_tip_price"],
    }
    print(f"...filling up with {transaction}")
    signed_txn = gas_station_account.sign_transaction(transaction)
    print(f"signed_txn {signed_txn}")
    print(f"from: {Account.recover_transaction(signed_txn.rawTransaction)}")
    tx_hash = W3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"filling up # {tx_hash.hex()}...")
    
    W3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transferred {CONFIGS['gas_station']['gas_allowance']} wei to {user_wallet_address}")
    return True
  except Exception as err:
    print(f"Error at Gas Station: {err}")
    return False