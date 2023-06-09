from enum import Enum
from typing import List, Union, Optional
from datetime import datetime
from pydantic import UUID4, ValidationError
import uuid

from pydantic import BaseModel, validator


############################
# Project section definition
############################


class ProjectBase(BaseModel):
    suanid: str
    name: str
    description: str
    categoryid: str 
    status: str

    class Config:
        orm_mode = True

class KoboFormId(str, Enum):
    parcelas = "parcelas"
    caracterizacion = "caracterizacion"
    postulacion = "postulacion"
############################
# User section definition
############################
class UserBase(BaseModel):
    username: str


class User(UserBase):
    id: UUID4
    id_wallet: Optional[str] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None


############################
# Wallet section definition
############################


class KeyCreate(BaseModel):
    name: Union[str, None]
    size: int = 24
    save_flag: bool = True


class KeyRecover(BaseModel):
    name: Union[str, None]
    words: List[str]
    save_flag: bool = True


# class KeyResponse(BaseModel):
#     save_flag: bool
#     id: UUID4
#     wallet_name: str
#     mnemonic:


############################
# Transaction section definition
############################


class NodeCommandName(str, Enum):
    utxos = "utxos"
    balance = "balance"


class AddressDestin(BaseModel):
    address: str
    amount: int


class SimpleSend(BaseModel):
    wallet_id: str
    address_destin: list[AddressDestin]
    metadata: Union[dict, None] = None
    witness: int = 1


class Tokens(BaseModel):
    name: str
    amount: int


class BuildTx(BaseModel):
    address_origin: str
    address_destin: list[AddressDestin]
    metadata: Union[dict, None] = None
    script_id: str = ""
    mint: Union[list[Tokens], None] = None
    witness: int = 1

    @validator("script_id", always=True)
    def chekc_script_id(cls, value):
        try:
            if value != "":
                uuid.UUID(value)
        except ValidationError as e:
            print(e)
        return value


class SimpleSign(BaseModel):
    wallets_ids: list[str]


class SignCommandName(str, Enum):
    cborhex = "cborhex"
    txfile = "txfile"


class Mint(SimpleSend):
    script_id: str
    tokens: list[Tokens]

    # @validator("script_id", always=True)
    # def chekc_script_id(cls, value):
    #     assert isinstance(value, UUID4), "Script_id field must be a valid UUID4"
    #     return value


############################
# Script section definition
############################


# class Script(BaseModel):
#     name: str
#     type: str = "all"
#     required: int = 0
#     hashes: List[str]
#     type_time: str = ""
#     slot: int = 0

#     @validator("type", always=True)
#     def check_type(cls, value):
#         if value not in ("sig", "all", "any", "atLeast"):
#             raise ValueError("type must be: sig, all, any or atLeast ")
#         return value

#     @validator("required", always=True)
#     def check_required(cls, value, values):
#         if values["type"] == "atLeast":
#             assert isinstance(
#                 value, int
#             ), "Required field must be integer if type atLeast is used"
#             assert (
#                 value > 0
#             ), "Required field must be higher than 0 and be equal to the number of specified keyHashes"
#         return value

#     @validator("hashes", always=True)
#     def check_hashes(cls, value, values):
#         if values["type"] == "atLeast":
#             assert (
#                 len(value) >= values["required"]
#             ), "Number of keyshashes should be atLeast equal to the number of required keyHashes"
#         return value

#     @validator("slot", always=True)
#     def check_slot(cls, value, values):
#         if values["type_time"] in ("before", "after"):
#             assert isinstance(
#                 value, int
#             ), "Slot field must be integer if type before/after is used"
#             assert (
#                 value > 0
#             ), "At least it should be greater than 0 or the current slot number"
#             return value
#         else:
#             return None


# class ScriptPurpose(str, Enum):
#     mint = "mint"
#     multisig = "multisig"
