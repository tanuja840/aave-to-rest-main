# web3_lib.py
"""
  NOTE: all the numbers in this file are in wei
"""
from web3 import Web3
from abis import (
  lending_pool_addresses_provider_abi,
  lending_pool_abi,
  protocol_data_provider_abi,
  erc20_abi,
)
from gas_station import top_up

# DTOs
from models import BalanceDTO

# Load Configs 
from pyaml_env import parse_config
CONFIGS = parse_config("./config.yaml")
NETWORK_CONFIGS = CONFIGS["networks"]
ADDRESS_CONFIGS = CONFIGS["tokens"]

# Supported tokens
USDC_ADDRESS = Web3.toChecksumAddress(ADDRESS_CONFIGS["USDC"]) # only USDC allowed

# ------------------------------------------------------------------------------
# Private methods
# ------------------------------------------------------------------------------

# boardcasts a raw transaction to the blockchain
def broadcast_transaction(transactionHex: str):
  try:
    tx_hash = W3.eth.send_raw_transaction(transactionHex)
    print("Waiting for transaction#", tx_hash.hex())
    W3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash
  except Exception as err:
    print(f"Error: broadcast_transaction() {err}")
    return False

def get_tx_status(tx_hash: str):
  print(f"Fetching transaction status...")
  try:
    status = W3.eth.get_transaction_receipt(tx_hash)
    print(f"...tx status {status}")
    return {
      "transactionIndex": status["transactionIndex"],
      "blockNumber": status["blockNumber"],

      "status": status["status"],
      "from": status["from"],
      "to": status["to"],
      "gasUsed": status["gasUsed"],
      "effectiveGasPrice": status["effectiveGasPrice"],

      "contractAddress": status["contractAddress"],
    }
  except Exception as err:
    print(f"Error: get_tx_status() {err}")
    return False

def get_reserve_data():
  print(f"Fetching Aave reserve data...")
  data = PROTOCOL_DATA_PROVIDER.functions.getReserveData(USDC_ADDRESS).call()
  print(f"data... {data}")
  data = {
    "availableLiquidity": data[0],
    "totalStableDebt": data[1],
    "totalVariableDebt": data[2],
    "liquidityRate": data[3],
    "variableBorrowRate": data[4],
    "stableBorrowRate": data[5],
    "averageStableBorrowRate": data[6],
    "liquidityIndex": data[7],
    "variableBorrowIndex": data[8],
    "lastUpdateTimestamp": data[9],
  }

  SEC_IN_YEAR = 31536000
  apr = float(int(data['liquidityRate']) / pow(10, 25))
  data["liquidityRateYearly"] = ((1 + (apr / 100) / SEC_IN_YEAR) ** SEC_IN_YEAR - 1) * 100

  apr = float(int(data['variableBorrowRate']) / pow(10, 25))
  data["variableBorrowRateYearly"] = ((1 + (apr / 100) / SEC_IN_YEAR) ** SEC_IN_YEAR - 1) * 100
  return data


def get_coin_reserve_data(coin_name:str):
  coin_name = coin_name.upper()
  if(ADDRESS_CONFIGS.get(coin_name) == None):
       print(f"{coin_name} not found")
       return False
  print(f"Fetching Aave reserve data for {coin_name}...")
  TOKEN_ADDRESS = Web3.toChecksumAddress(ADDRESS_CONFIGS[coin_name])
  data = PROTOCOL_DATA_PROVIDER.functions.getReserveData(TOKEN_ADDRESS).call()
  print(f"reserve data received: {data}")
  data = {
    "availableLiquidity": data[0],
    "totalStableDebt": data[1],
    "totalVariableDebt": data[2],
    "liquidityRate": data[3],
    "variableBorrowRate": data[4],
    "stableBorrowRate": data[5],
    "averageStableBorrowRate": data[6],
    "liquidityIndex": data[7],
    "variableBorrowIndex": data[8],
    "lastUpdateTimestamp": data[9],
  }

  SEC_IN_YEAR = 31536000
  apr = float(int(data['liquidityRate']) / pow(10, 25))
  data["liquidityRateYearly"] = ((1 + (apr / 100) / SEC_IN_YEAR) ** SEC_IN_YEAR - 1) * 100

  apr = float(int(data['variableBorrowRate']) / pow(10, 25))
  data["variableBorrowRateYearly"] = ((1 + (apr / 100) / SEC_IN_YEAR) ** SEC_IN_YEAR - 1) * 100
  return data
# -----------------------------
# Balance
# -----------------------------

# Estimate required gas units for the given transaction data
def estimate_gas_units(transaction):
  print(f"Estimating gas units...")
  try:
    gas_units = int(W3.eth.estimate_gas(transaction)) * 3 # 3X the estimate to be safe
    print(f"...estimated gas units: {gas_units}")
  except Exception as err:
    print(f"ERROR: in estimate_gas_units() {err}")
    gas_units = NETWORK_CONFIGS["default_gas_units"]

  return gas_units

# Check if the wallet has enough gas amount for the transaction
def fuel_gauge(transaction):
  print("Running fuel check...")
  gas_price = NETWORK_CONFIGS["gas_price"]
  gas_units = estimate_gas_units(transaction)

  try:
    matic_bal = int(get_native_balance(transaction['from']))
    print(f"...available fuel: {matic_bal}")
  except Exception as err:
    print(f"ERROR: in fuel_gauge() {err}")
    return False
  
  has_fuel = matic_bal > (gas_price * gas_units)
  if has_fuel is False:
    print(f"ERROR: not enough gas! Current: {matic_bal}, required: {gas_price * gas_units}")
  else:
    print(f"...fuel check pass")
  return has_fuel

# Get balance of a token with given contract address using balanceOf()
def get_balance(token_address, wallet_address, token_name):
  print("Fetching balance...")

  ERC20_contract = W3.eth.contract(address=token_address, abi=erc20_abi)
  token_address = Web3.toChecksumAddress(token_address)
  wallet_address = Web3.toChecksumAddress(wallet_address)
  amount_wei = ERC20_contract.functions.balanceOf(wallet_address).call()
  print(f"{token_name} balance is {amount_wei} wei for contract {token_address}")
  
  return amount_wei

# Native token balance, i.e. MATIC
def get_native_balance(wallet_address: str):
  print("Fetching native balance...")

  wallet_address = Web3.toChecksumAddress(wallet_address)
  amount_wei = W3.eth.getBalance(wallet_address)
  print(f"...native balance is {amount_wei} wei")
  
  return amount_wei

# -----------------------------
# Deposit
def deposit_to_aave(balance: BalanceDTO, wallet_address: str, nonce: int = None):
  print("Depositing to Aave...")

  if nonce is None:
    nonce = W3.eth.getTransactionCount(wallet_address)
  print(f"Nonce is {nonce}")

  wallet_address = Web3.toChecksumAddress(wallet_address)
  amount = balance["USDC"]
  refferal_code = 0 # this is legacy code

  function_call = LENDING_POOL.functions.deposit(USDC_ADDRESS, amount, wallet_address, refferal_code)
  transaction = function_call.buildTransaction({
    "chainId": NETWORK_CONFIGS["chain_id"],
    "from": wallet_address,
    "nonce": nonce,
    "gas": NETWORK_CONFIGS["default_gas_units"],
    "maxFeePerGas": NETWORK_CONFIGS["gas_price"],
    "maxPriorityFeePerGas": NETWORK_CONFIGS["miner_tip_price"],
  })
  transaction['gas']  = estimate_gas_units(transaction)

  if fuel_gauge(transaction):
    return transaction
  else:
    top_up(wallet_address)
    return transaction

# -----------------------------
# Allowance
def approve_for_aave(balance: BalanceDTO, wallet_address: str):
  print("Approval for Aave...")

  wallet_address = Web3.toChecksumAddress(wallet_address)
  nonce = W3.eth.getTransactionCount(wallet_address)
  amount = balance["USDC"]

  ERC20_contract = W3.eth.contract(address=USDC_ADDRESS, abi=erc20_abi)
  function_call = ERC20_contract.functions.approve(LENDING_POOL.address, amount)
  transaction = function_call.buildTransaction({
    "chainId": NETWORK_CONFIGS["chain_id"],
    "from": wallet_address,
    "nonce": nonce,
    "gas": NETWORK_CONFIGS["default_gas_units"],
    "maxFeePerGas": NETWORK_CONFIGS["gas_price"],
    "maxPriorityFeePerGas": NETWORK_CONFIGS["miner_tip_price"],
  })
  transaction['gas']  = estimate_gas_units(transaction)

  if fuel_gauge(transaction):
    return transaction
  else:
    top_up(wallet_address)
    return transaction


# ------------------------------------------------------------------------------
# Private methods
# ------------------------------------------------------------------------------
def get_lending_pool():
  print("Resolving pool addresses...")
  lending_pool_addresses_provider_address = Web3.toChecksumAddress(
    NETWORK_CONFIGS["lending_pool_addresses_provider"]
  )
  lending_poll_addresses_provider = W3.eth.contract(
    address=lending_pool_addresses_provider_address,
    abi=lending_pool_addresses_provider_abi,
  )

  # LENDING POOL
  lending_pool_address = lending_poll_addresses_provider.functions.getLendingPool().call()
  print("lending_pool_address", lending_pool_address)
  return
  lending_pool = W3.eth.contract(address=lending_pool_address, abi=lending_pool_abi)

  # PROTOCOL DATA PROVIDER
  protocol_data_provider_address = NETWORK_CONFIGS["protocol_data_provider_address"]
  protocol_data_provider = W3.eth.contract(address=protocol_data_provider_address, abi=protocol_data_provider_abi)
  return lending_pool, protocol_data_provider

# ------------------------------------------------------------------------------
# Web3 setup
W3 = Web3(Web3.HTTPProvider(NETWORK_CONFIGS["rpc_url"]))
LENDING_POOL, PROTOCOL_DATA_PROVIDER = get_lending_pool()
