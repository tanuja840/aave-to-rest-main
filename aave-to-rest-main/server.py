# server.py
import time
from typing import Optional

# Fast API
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# Web3
from web3 import Web3

# Load Configs 
from pyaml_env import parse_config
CONFIGS = parse_config("./config.yaml")
NETWORK_CONFIGS = CONFIGS["networks"]
ADDRESS_CONFIGS = CONFIGS["tokens"]
DECIMAL_CONFIGS = CONFIGS["decimals"]

# ------------------------------------------------------------------------------
# Fast API
# ------------------------------------------------------------------------------
app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins = CONFIGS["fastAPI"]["origins"],
  allow_credentials = True,
  allow_methods = ["OPTION", "GET", "POST"],
  allow_headers = ["*"],
)

# FastAPI Authentication Hook
# @app.middleware("http")
# async def check_oauth(request: Request, call_next):
#   try:
#     X_Auth_Token = request.headers['X-Auth-Token']
#     # TODO: Do the Cypher decode and auth token validation
#   except Exception as err:
#     print(f"Error in middleware for X_Auth_Token {err}")
#     X_Auth_Token = None
  
#   if X_Auth_Token is not None:
#     return await call_next(request)
#   else:
#     return JSONResponse(send(False, 401, "user not authenticated"))

@app.get("/test")
def test_api():
  return send(msg="Yay! Server running!")

# ------------------------------------------------------------------------------
# API Methods
# ------------------------------------------------------------------------------
from models import BalanceDTO, WalletDTO, RawTransactionDTO
from gas_station import top_up
from web3_lib import broadcast_transaction, get_tx_status, get_reserve_data, get_coin_reserve_data
from web3_lib import get_balance, get_native_balance
from web3_lib import approve_for_aave, deposit_to_aave

# ----------------------------------------------
# Interact with RPC
# TODO: implement redis store for rate limiting
@app.post("/broadcast")
def broadcast(transaction: RawTransactionDTO):
  tx_hash = broadcast_transaction(transaction.hex)
  if tx_hash == False:
    return send(success=False)
  else:
    return send(data={"transactionHash": str(tx_hash)})

@app.get("/status/{tx_hash}")
def status(tx_hash: str):
  status = get_tx_status(tx_hash)
  return send(data=status)

@app.get("/reserves")
def status():
  data = get_reserve_data()
  return send(data=data)

@app.get("/coin_reserves/{coin_name}")
def status(coin_name: str):
  data = get_coin_reserve_data(coin_name)
  if data == False:
    return send(success=False)
  else:
    return send(data=data)

# ----------------------------------------------
# TODO: implement redis store for rate limiting
@app.get("/balance/{wallet_address}")
def fetch_balance(wallet_address: str):
  print(f"[GET] /balance/{wallet_address}...")

  data = {"timestamp": time.time() * 1000}
  data["MATIC"] = get_native_balance(wallet_address)
  for token in ["amUSDC", "USDC"]:
    address = Web3.toChecksumAddress(ADDRESS_CONFIGS[token])
    data[token] = get_balance(
      token_address=address,
      wallet_address=wallet_address,
      token_name=token
    )
    # NOTE: Be careful with the following code
    data[token + "_decimal"] = Web3.fromWei(data[token], DECIMAL_CONFIGS[token])

  return send(msg="", data=data)


# ----------------------------------------------
# TODO: implement redis store for rate limiting
# TODO: Security risk
@app.post("/gas_station")
def gas_station(wallet: WalletDTO):
  balanceRes = fetch_balance(wallet.address)
  balanceData = balanceRes["data"]

  if balanceData["MATIC"] <= CONFIGS["gas_station"]["reserved_gas"]:
    success = top_up(wallet.address)
    if success:
      return send("Gas filled!")
    else:
      return send(False, 500, "Something went wrong, please try again")
  else:
    return send(False, 200, "Gas not empty!")

# ----------------------------------------------
# POST /allowance
# Get transaction to be signed for allowance approval
@app.post("/allowance")
def allowance(wallet: WalletDTO, balanceData: Optional[BalanceDTO] = None):
  if balanceData is None:
    balanceRes = fetch_balance(wallet.address)
    balanceData = balanceRes["data"]
  tx_allowance = approve_for_aave(balanceData, wallet.address)
  return send(data={"tx_allowance": tx_allowance})

# POST /deposit
# Deposits all the non aTokens to the Aave USDC pool
@app.post("/deposit")
def deposit(wallet: WalletDTO, X_Auth_Token: str = Header(None)):
  # balance
  balanceRes = fetch_balance(wallet.address)
  balanceData: BalanceDTO = balanceRes["data"]

  # check if sufficient fund is there
  if balanceData["MATIC"] <= CONFIGS["gas_station"]["reserved_gas"]:
    top_up(wallet.address)
  
  # allowance
  res = allowance(wallet, balanceData)
  tx_allowance = res["data"]["tx_allowance"]
  if tx_allowance is not False:
    nonce = tx_allowance["nonce"] + 1
  
  # depsit
  tx_deposit = deposit_to_aave(balanceData, wallet.address, nonce)
  return send(data={
    "balanceData": balanceData,
    "txAllowance": tx_allowance,
    "txDeposit": tx_deposit,
    })

# ------------------------------------------------------------------------------
# API Helpers
# ------------------------------------------------------------------------------
def send(success: bool = True, code: int = 200, msg: str = "", data = None):
  print("\n\n")
  return {
    'status': success,
    'code': code,
    'msg': msg,
    'data': data
  }

