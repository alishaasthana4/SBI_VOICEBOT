import os
import json
import base64
import requests
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv
import logging
load_dotenv(override=True)
 
SBI_API_ENDPOINT = os.getenv("SBI_API_ENDPOINT", "https://devapi.sbigeneral.in")
CLIENT_ID = os.getenv("SBI_CLIENT_ID")
CLIENT_SECRET = os.getenv("SBI_CLIENT_SECRET")
AES_KEY = b"cH1NXn7FpWmXrJxyu+MLYUmcW2oTagHu"
AES_IV = b"yLNhTgqH4wA="
logging.info(f"SBI_API_ENDPOINT: {SBI_API_ENDPOINT}")
 
logging.info(f"CLIENT_ID: {CLIENT_ID}")
 
logging.info(f"CLIENT_SECRET: {CLIENT_SECRET}")
 
logging.info(f"AES_KEY: {AES_KEY}")
 
logging.info(f"AES_IV: {AES_IV}")
 
 
# ====================================================================
# Function to encrypt plaintext payload using AES-256-GCM
# ====================================================================
def encrypt_payload(plaintext: dict) -> str:
    """
    Encrypts a dictionary payload using AES-256-GCM.
 
    Args:
        plaintext (dict): The data to encrypt.
 
    Returns:
        str: Base64-encoded encrypted payload including ciphertext and tag.
    """
    json_bytes = json.dumps(plaintext).encode('utf-8')
    logging.info(f"json_bytes: {json_bytes}")
 
    encryptor = Cipher(
        algorithms.AES(AES_KEY),
        modes.GCM(AES_IV),
        backend=default_backend()
    ).encryptor()
 
    ciphertext = encryptor.update(json_bytes) + encryptor.finalize()
    encrypted = ciphertext + encryptor.tag
    return base64.b64encode(encrypted).decode('utf-8')
 
# ====================================================================
# Function to decrypt base64-encoded ciphertext using AES-256-GCM
# ====================================================================
def decrypt_payload(ciphertext_b64: str) -> dict:
    """
    Decrypts a base64-encoded AES-256-GCM encrypted payload.
 
    Args:
        ciphertext_b64 (str): The encrypted payload.
 
    Returns:
        dict: The decrypted JSON data.
    """
    encrypted_data = base64.b64decode(ciphertext_b64)
    ciphertext = encrypted_data[:-16]
    tag = encrypted_data[-16:]
 
    decryptor = Cipher(
        algorithms.AES(AES_KEY),
        modes.GCM(AES_IV, tag),
        backend=default_backend()
    ).decryptor()
 
    decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
    return json.loads(decrypted_bytes.decode('utf-8'))
 
# ====================================================================
# Function to get access token (static or implement refresh if needed)
# ====================================================================
def generate_access_token() -> str:
    """
    Generates a new access token from SBI General Insurance API.
 
    Returns:
        str: The access token as a Bearer token string.
 
    Raises:
        Exception: If the token generation fails.
    """
    url = f"{SBI_API_ENDPOINT}/v1/tokens"
    logging.info(f"generate_access_token: url: {url}")
    headers = {
        "X-IBM-Client-Id": CLIENT_ID,
        "X-IBM-Client-Secret": CLIENT_SECRET,
    }
 
    response = requests.get(url, headers=headers, timeout=5)
 
    if response.status_code != 200:
        raise Exception(f"Failed to generate access token: {response.status_code} - {response.text}")
 
    token_data = response.json()
    logging.info(f"generate_access_token: token_data: {token_data}")
 
    # Assuming the token is returned in the field 'access_token'
    access_token = token_data.get("accessToken")
    if not access_token:
        raise Exception("Access token not found in response")
    return str(access_token)
 
 
# ====================================================================
# Function to call SBI General API
# ====================================================================
def get_user_policies(phone: str, policy_no: str = None) -> dict:
    """
    Calls the SBI General API with encrypted payload and returns decrypted response.
 
    Args:
        service_path (str): API service path (e.g., '/Customer/SearchCustomer').
        payload (dict): The plaintext JSON payload.
 
    Returns:
        dict: The decrypted JSON response.
    """
    try:
        token = generate_access_token()
        logging.info(f"token: {token}")
 
        if policy_no:
            payload = {
                "policy_number": policy_no
            }
        else:
            # payload = {
            #     "phone_number": phone
            # }
 
            payload = {
                "phone_number": "8320441987"
            }
        endpoint = f"{SBI_API_ENDPOINT}/SOA12C/services/Customer/SearchCustomer"
        logging.info(f"endpoint: {endpoint}, payload: {payload}")
 
        encrypted = encrypt_payload(payload)
        logging.info(f"encrypted: {encrypted}")
 
        headers = {
            "Authorization": token,
            "X-IBM-Client-Id": CLIENT_ID,
            "X-IBM-Client-Secret": CLIENT_SECRET,
            "Content-Type": "application/json"
        }
 
        response = requests.post(
            endpoint,
            headers=headers,
            json={"ciphertext": encrypted},
            timeout=5
        )
 
        if response.status_code != 200:
            logging.error(f"API call failed with status {response.status_code}: {response.text}")
            return {
                "status": "error",
                "data": None,
                "message": f"API call failed with status {response.status_code}"
            }
 
        response_json = response.json()
        logging.info(f"response_json: {response_json}")
        decrypted_response = decrypt_payload(response_json['ciphertext'])
        logging.info(f"decrypted_response: {decrypted_response}")
 
        # decrypted_response = {"CustomerData":[{"policyNumber":10000001,"customerName":"Rishabh Vaishya","panNumber":"BGSPV5555L","registeredMobile":8320441987,"registeredEmail":"vaishya.rishabh@sbigeneral.in","policyType":"Motor","vehicleNumber":"GJ05KZ9000","chassisNumber":"ME1RG674CM0010582","rtoState":"Gujarat","alternatePolicyNum":"POSP/2134123-123"},{"policyNumber":10000111,"customerName":"Rishabh Vaishya","panNumber":"BGSPV5555L","registeredMobile":8320441987,"registeredEmail":"vaishya.rishabh@sbigeneral.in","policyType":"Health","vehicleNumber":None,"chassisNumber":None,"rtoState":None,"alternatePolicyNum":None}]}
 
        return {
            "status": "success",
            "data": decrypted_response,
            "message": "Data decrypted successfully"
        }
   
    except Exception as e:
        logging.exception("Exception during API call or decryption")
        return {
            "status": "error",
            "data": None,
            "message": f"Exception occurred: {str(e)}"
        }
   
 
 
def get_claim_intimation(policy_no, accident_date, accident_time, time_mode, accident_city, accident_state, who_drive) -> dict:
    """
    Calls the SBI General API with encrypted payload and returns decrypted response.
 
    Args:
        service_path (str): API service path (e.g., '/Customer/SearchCustomer').
        payload (dict): The plaintext JSON payload.
 
    Returns:
        dict: The decrypted JSON response.
    """
    try:
        token = generate_access_token()
        logging.info(f"token: {token}")
 
        date_obj = datetime.strptime(accident_date, "%d/%m/%Y")
        formatted_date = date_obj.strftime("%Y-%m-%d")
 
        time_12hr = f"{accident_time} {time_mode}"
        datetime_obj = datetime.strptime(f"{accident_date} {time_12hr}", "%d/%m/%Y %I:%M:%S %p")
        formatted_datetime = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
 
        payload = {
            "accident_state": accident_state,
            "policy_number": str(policy_no),
            "accident_time": formatted_datetime,
            "accident_city": accident_city,
            "driver_passenger": who_drive,
            "accident_date": formatted_date,
            "accident_pin": "1234"
        }
        endpoint = f"{SBI_API_ENDPOINT}/SOA12C/services/Customer/ClaimIntimation"
        logging.info(f"endpoint: {endpoint}, payload: {payload}")
        
        encrypted = encrypt_payload(payload)
        logging.info(f"encrypted: {encrypted}")
        headers = {
            "Authorization": token,
            "X-IBM-Client-Id": CLIENT_ID,
            "X-IBM-Client-Secret": CLIENT_SECRET,
            "Content-Type": "application/json"
        }
 
        response = requests.post(
            endpoint,
            headers=headers,
            json={"ciphertext": encrypted}
        )
 
        if response.status_code != 200:
            logging.error(f"API call failed with status {response.status_code}: {response.text}")
            return {
                "status": "error",
                "data": None,
                "message": f"API call failed with status {response.status_code}"
            }
 
        response_json = response.json()
        logging.info(f"response_json: {response_json}")
 
        decrypted_response = decrypt_payload(response_json['ciphertext'])
        logging.info(f"decrypted_response: {decrypted_response}")
 
        # decrypted_response = {'policy_number': 10000001, 'claim_number': 1014, 'claim_status': 'Success'}
        return {
            "status": "success",
            "data": decrypted_response,
            "message": "Data decrypted successfully"
        }
   
    except Exception as e:
        logging.exception("Exception during API call or decryption")
 
        return {
            "status": "error",
            "data": None,
            "message": f"Exception occurred: {str(e)}"
        }
   
def insert_policy(policy_no: str, email: str) -> dict:
    """
    Calls the SBI General API to verify policy number and email ID.
 
    Args:
        policy_no (str): The policy number.
        email (str): The email ID to verify.
 
    Returns:
        dict: The decrypted JSON response or an error structure.
    """
    try:
        token = generate_access_token()
        logging.info(f"token: {token}")
 
        payload = {
            "policy_number": policy_no,
            "email_id": email
        }
        endpoint = f"{SBI_API_ENDPOINT}/SOA12C/services/Customer/InsertPolicyPDF"
        logging.info(f"endpoint: {endpoint}, payload: {payload}")
 
        encrypted = encrypt_payload(payload)
        logging.info(f"encrypted: {encrypted}")
        headers = {
            "Authorization": token,
            "X-IBM-Client-Id": CLIENT_ID,
            "X-IBM-Client-Secret": CLIENT_SECRET,
            "Content-Type": "application/json"
        }
 
        response = requests.post(
            endpoint,
            headers=headers,
            json={"ciphertext": encrypted}
        )
 
        if response.status_code != 200:
            logging.error(f"API call failed with status {response.status_code}: {response.text}")
            return {
                "status": "error",
                "data": None,
                "message": f"API call failed with status {response.status_code}"
            }
 
        response_json = response.json()
        logging.info(f"response_json: {response_json}")
 
        decrypted_response = decrypt_payload(response_json['ciphertext'])
        logging.info(f"decrypted_response: {decrypted_response}")
        # decrypted_response = {'ccmId': 1034, 'status': 'Success'}
 
        return {
            "status": "success",
            "data": decrypted_response,
            "message": "Data decrypted successfully"
        }
 
    except Exception as e:
        logging.exception("Exception during API call or decryption")
        return {
            "status": "error",
            "data": None,
            "message": f"Exception occurred: {str(e)}"
        }
 
def update_email(policy_no: str, email: str, otp_verified: bool) -> dict:
    """
    Calls the SBI General API to verify policy number, email ID, and OTP status.
 
    Args:
        policy_number (str): The policy number (alphanumeric).
        email_id (str): The email address (must be a valid email).
        otp_verified (bool): Whether the user has verified OTP (True/False).
 
    Returns:
        dict: The decrypted JSON response or an error structure.
    """
    try:
        token = generate_access_token()
        logging.info(f"token: {token}")
 
        payload = {
            "policyNumber": policy_no,
            "otpVerified": otp_verified,
            "emailId": email            
        }
        endpoint = f"{SBI_API_ENDPOINT}/SOA12C/services/Customer/UpdateEmail"
        logging.info(f"endpoint: {endpoint}, payload: {payload}")
 
        encrypted = encrypt_payload(payload)
        logging.info(f"encrypted payload: {encrypted}")
 
        headers = {
            "Authorization": token,
            "X-IBM-Client-Id": CLIENT_ID,
            "X-IBM-Client-Secret": CLIENT_SECRET,
            "Content-Type": "application/json"
        }
 
        response = requests.post(
            endpoint,
            headers=headers,
            json={"ciphertext": encrypted}
        )
 
        if response.status_code != 200:
            logging.error(f"API call failed with status {response.status_code}: {response.text}")
            return {
                "status": "error",
                "data": None,
                "message": f"API call failed with status {response.status_code}"
            }
 
        response_json = response.json()
        logging.info(f"response_json: {response_json}")
 
        decrypted_response = decrypt_payload(response_json['ciphertext'])
        logging.info(f"decrypted_response: {decrypted_response}")
 
        # decrypted_response = {'service_request_id': 1090, 'status': 'Success'}
 
        return {
            "status": "success",
            "data": decrypted_response,
            "message": "Data decrypted successfully"
        }
 
    except Exception as e:
        logging.exception("Exception during API call or decryption")
        return {
            "status": "error",
            "data": None,
            "message": f"Exception occurred: {str(e)}"
        }
