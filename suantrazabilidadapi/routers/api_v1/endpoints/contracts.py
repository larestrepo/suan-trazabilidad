import logging
from opshin.prelude import TxOutRef, TxId
from pycardano import (
    Address,
    ScriptHash
)
from opshin.builder import build, PlutusContract
from fastapi import APIRouter, HTTPException
from typing import Optional

from suantrazabilidadapi.utils.blockchain import Keys, CardanoNetwork
from suantrazabilidadapi.utils.generic import Constants, is_valid_hex_string
from suantrazabilidadapi.utils.plataforma import Plataforma
from suantrazabilidadapi.routers.api_v1.endpoints import pydantic_schemas


router = APIRouter()

@router.post("/get-pkh/{pkh_command}", status_code=201,
summary="From address or wallet name obtain pkh. If wallet name is provided, it has to exist locally",
    response_description="script hash",)

async def getPkh(command_name: pydantic_schemas.walletCommandName, wallet: str) -> str:
    """From address or wallet name obtain pkh. If wallet name is provided, it has to exist locally\n
    """
   
    try:      
        if command_name == "address":
            address = wallet
            final_response = Keys().getPkh(address)
               
        elif command_name == "id":
            if not is_valid_hex_string(wallet):
                raise ValueError(f"id provided does not exist in wallet database") 
            
            r = Plataforma().getWallet(command_name, wallet)

            if r["data"].get("data", None) is not None:
                    
                walletInfo = r["data"]["data"]["getWallet"]
                if walletInfo is None:
                    final_response = "Wallet not found"
                else:
                    address = walletInfo["address"]
                    final_response = Keys().getPkh(address)
            else:
                final_response = "Error fetching wallet info"

        return final_response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/get-scripts/", status_code=200,
summary="Get all the scripts registered in Plataforma",
    response_description="Script details",)

async def getScripts():
    """Get all the scripts registered in Plataforma
    """
    try:
        r = Plataforma().listScripts()
        if r["data"].get("data", None) is not None:
            script_list = r["data"]["data"]["listScripts"]["items"]
            if script_list == []:
                final_response = {
                    "success": True,
                    "msg": 'No scripts present in the table',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'List of scripts',
                    "data": script_list
                }
        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
        
        return final_response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/get-script/{script_type}", status_code=200,
summary="Read script created",
    response_description="script details")

async def getScript(script_type: pydantic_schemas.contractCommandName, query_param: str) -> dict:

    if script_type == "id":

        r = Plataforma().getScript(script_type, query_param)

        if r["data"].get("data", None) is not None:
            contractInfo = r["data"]["data"]["getScript"]
                
            if contractInfo is None:
                final_response = {
                    "success": True,
                    "msg": f'Contract with id: {query_param} does not exist in DynamoDB',
                    "data": r["data"]
                }
            else:
                final_response = {
                    "success": True,
                    "msg": 'Contract info',
                    "data": contractInfo
                }

        else:
            if r["success"] == True:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["data"]["errors"]
                }
            else:
                final_response = {
                    "success": False,
                    "msg": "Error fetching data",
                    "data": r["error"]
                }
    
    return final_response


@router.get("/create-contract/{script_type}", status_code=200,
summary="From parameters build and create the smart contract",
    response_description="script details")

async def createContract(script_type: pydantic_schemas.ScriptType, name: str, wallet_id: str, tokenName: str = "", save_flag: bool = True, parent_policy_id: Optional[str] = None, project_id: Optional[str] = None) -> dict:

    """From parameters build a smart contract
    """
    try:

        #TODO: Verify that the wallet is admin
        #TODO: Use project_id variable or delete it

        r = Plataforma().getWallet("id", wallet_id)
        if r["data"].get("data", None) is not None:
            walletInfo = r["data"]["data"]["getWallet"]
                
            if walletInfo is None:
                raise ValueError(f'Wallet with id: {wallet_id} does not exist in DynamoDB')
            else:
                # Get payment address
                payment_address = Address.from_primitive(walletInfo["address"])
                pkh = bytes(payment_address.payment_part)

        else:
            raise ValueError(f'Error fetching data')

        tn_bytes = bytes(tokenName, encoding="utf-8")

        if script_type == "mintSuanCO2":
            scriptCategory = "PlutusV2"
            script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("suanco2.py")
            contract = build(script_path, pkh, tn_bytes)

        
        elif script_type == "mintProjectToken":
            
            chain_context = CardanoNetwork().get_chain_context()
            utxo_to_spend = None
            for utxo in chain_context.utxos(payment_address):
                if utxo.output.amount.coin > 3000000:
                    utxo_to_spend = utxo
                    break
            assert utxo_to_spend is not None, "UTxO not found to spend!"
            oref = TxOutRef(
                id=TxId(bytes(utxo_to_spend.input.transaction_id)),
                idx=utxo_to_spend.input.index,
            )

            logging.info(f"oref found to build the script: {oref.id.to_cbor_hex()} and idx: {oref.idx}")

            script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("project.py")
            scriptCategory = "PlutusV2"
            # project_bytes = bytes(project_id, encoding="utf-8")
            contract = build(script_path, oref, pkh, tn_bytes)
        
        elif script_type == "spend":
            scriptCategory = "PlutusV2"
            script_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR).joinpath("inversionista.py")
            
            contract = build(script_path, bytes.fromhex(parent_policy_id), tn_bytes)

        # Build the contract
        plutus_contract = PlutusContract(contract)

        cbor_hex = plutus_contract.cbor_hex
        mainnet_address = plutus_contract.mainnet_addr
        testnet_address = plutus_contract.testnet_addr
        policy_id = plutus_contract.policy_id

        logging.info(f"Build contract with policyID: {policy_id} and testnet address: {testnet_address}")

        ##################

        r = Plataforma().getScript("id", policy_id)
        if r["success"] == True:
            if r["data"]["data"]["getScript"] is None:
                # It means that the Script does not exist in database, so update database if save_flag is True
                if save_flag:
                    # Build the variables and store in DynamoDB
                    variables = {
                        "id": policy_id,
                        "name": name,
                        "MainnetAddr": mainnet_address.encode(),
                        "testnetAddr": testnet_address.encode(),
                        "cbor": cbor_hex,
                        "pbk": wallet_id,
                        "script_category": scriptCategory,
                        "script_type": script_type,
                        "Active": True,
                        "token_name": tokenName,

                    }
                    # Check if project_id was provided
                    if script_type != "mintSuanCO2" and not project_id:
                        raise ValueError(f'Project Id must be provided to interact with this contract')
                    else:
                        # Validate that the project exists in table products
                        r = Plataforma().getProject("id", project_id)
                        if not r["data"].get("data", None) or not r["data"]["data"]["getProduct"]:
                            raise ValueError(f'Project with id {project_id} does not exist in DynamoDB')
                        
                        variables["productID"] = project_id
                    

                    responseScript = Plataforma().createContract(variables)
                    if responseScript["success"] == True:
                        if responseScript["data"]["data"] is not None:
                            final_response = {"success": True, "msg": f'Script created', "data": {
                                "id": policy_id,
                            }}
                        else: 
                            final_response = {"success": False, "msg": f'Problems creating the cript with id: {policy_id} in dynamoDB'}
                    else:
                         final_response = {"success": False, "msg": f'Problems creating the script', "data": responseScript["error"]}
                else:
                    final_response = {"success": True, "msg": f'Script created but not stored in Database', "data": {
                            "id": policy_id,
                            "mainnet_address": mainnet_address.encode(),
                            "testnet_address": testnet_address.encode(),
                            "cbor": cbor_hex,
                    }}
            else:
                final_response = {
                    "success": True,
                    "msg": f'Script with id: {policy_id} already exists in DynamoDB',
                    "data": r["data"]
                }
        else:
            final_response = {
                "success": False,
                "msg": "Error fetching data",
                "data": r["error"]
            }

        return final_response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/save-contracts/", status_code=201,
summary="Save all the contracts to S3 available locally in the system",
    response_description="script details",)

async def saveContracts() -> dict:
    """Save all the contracts to S3 which are available locally in the system
    """
    contracts_path = Constants.PROJECT_ROOT.joinpath(Constants.CONTRACTS_DIR)
    result = Plataforma().upload_folder(contracts_path)
    return result

@router.get("/list-contracts/", status_code=201,
summary="List all the contracts available in S3",
    response_description="script details",)

async def listContracts() -> list:
    """List all the contracts available in S3
    """
    result = Plataforma().list_files("public/contracts")
    return result










# @click.command()
# @click.argument("wallet_name")
# @click.argument("token_name")
# @click.option( "--amount", type=int, default=1)
# @click.option(
#     "--script",
#     type=click.Choice(["free", "nft", "signed"]),
#     default="nft",
# # )
# def main(wallet_name: str, token_name: str, amount: int, script: str):
#     # Load chain context
#     context = get_chain_context()

#     # Get payment address
#     payment_address = get_address(wallet_name)

#     # Get input utxo
#     utxo_to_spend = None
#     for utxo in context.utxos(payment_address):
#         if utxo.output.amount.coin > 3000000:
#             utxo_to_spend = utxo
#             break
#     assert utxo_to_spend is not None, "UTxO not found to spend!"

#     tn_bytes = bytes(token_name, encoding="utf-8")
#     signatures = []
#     if script == "nft":
#         # Build script
#         script_path = lecture_dir.joinpath("nft.py")
#         oref = TxOutRef(
#             id=TxId(bytes(utxo_to_spend.input.transaction_id)),
#             idx=utxo_to_spend.input.index,
#         )
#         plutus_script = build(script_path, oref, tn_bytes)
#     elif script == "signed":
#         # Build script
#         script_path = lecture_dir.joinpath("signed.py")
#         pkh = bytes(get_address(wallet_name).payment_part)
#         signatures.append(VerificationKeyHash(pkh))
#         plutus_script = build(script_path, pkh)
#     else:
#         cbor_path = assets_dir.joinpath(script, "script.cbor")
#         with open(cbor_path, "r") as f:
#             cbor_hex = f.read()
#         cbor = bytes.fromhex(cbor_hex)
#         plutus_script = PlutusV2Script(cbor)

#     # Load script info
#     script_hash = plutus_script_hash(plutus_script)

#     # Build the transaction
#     builder = TransactionBuilder(context)
#     builder.add_minting_script(script=plutus_script, redeemer=Redeemer(0))
#     builder.mint = MultiAsset.from_primitive({bytes(script_hash): {tn_bytes: amount}})
#     if amount > 0:
#         builder.add_input(utxo_to_spend)
#         builder.add_output(
#             TransactionOutput(
#                 payment_address, amount=Value(coin=2000000, multi_asset=builder.mint)
#             )
#         )
#     else:
#         assert script != "nft", "lecture nft script doesn't allow burning"
#         burn_utxo = None

#         def f(pi: ScriptHash, an: AssetName, a: int) -> bool:
#             return pi == script_hash and an.payload == tn_bytes and a >= -amount

#         for utxo in context.utxos(payment_address):
#             if utxo.output.amount.multi_asset.count(f):
#                 burn_utxo = utxo
#         builder.add_input(burn_utxo)
#         assert burn_utxo, "UTxO containing token not found!"

#     builder.required_signers = signatures

#     # Sign the transaction
#     payment_vkey, payment_skey, payment_address = get_signing_info(wallet_name)
#     signed_tx = builder.build_and_sign(
#         signing_keys=[payment_skey],
#         change_address=payment_address,
#     )

#     # Submit the transaction
#     context.submit_tx(signed_tx)

#     print(f"transaction id: {signed_tx.id}")
#     print(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")
