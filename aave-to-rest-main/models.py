from pydantic import BaseModel, ValidationError, validator
from typing import Optional

# 
class depositDTO(BaseModel):
  mobile: str
  otp: int

  @validator('mobile')
  def mobile_should_be_valid(cls, v):
    if len(v) < 12 or len(v) > 13:
      raise ValueError('Please provide a valid mobile number')
    elif '+' not in v:
      raise ValueError('please provide a valid mobile number with country code')
    return v.replace(' ', '')

# 
class WalletDTO(BaseModel):
  address: str

  @validator('address')
  def is_valid_address(cls, address):
    if len(address) != 42:
      raise ValueError('Please provide a valid wallet address')
    return address

# 
class RawTransactionDTO(BaseModel):
  hex: str

# 
class BalanceDTO(BaseModel):
  timestamp: float
  
  MATIC: float
  amUSDC: float
  USDC: float

  MATIC_decimal: float
  amUSDC_decimal: float
  USDC_decimal: float
  