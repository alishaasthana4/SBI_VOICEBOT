from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import re
import unicodedata
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from api import get_user_policies, insert_policy
from prompts import (
    POLICY_NUMBER_PROMPT, OTP_PROMPT, DATE_OF_ACCIDENT_PROMPT, TIME_OF_ACCIDENT_PROMPT,
    AM_PM_PROMPT, CITY_OF_ACCIDENT_PROMPT, STATE_OF_ACCIDENT_PROMPT,
    EMAIL_ID_PROMPT, WHO_DRIVER_PROMPT, GUJARATI_DIGIT_MAP, HINDI_FULL_DIGIT_MAP,
    HINDI_SINGLE_DIGIT_MAP, MARATHI_DIGIT_MAP, LANGUAGE_STRINGS,
    AM_PM_KEYWORDS, ENGLISH_DIGIT_MAP, dont_know_phrases, PROMPTS
)
import logging
from typing import Optional

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

class StartFlowRequest(BaseModel):
    session_id: str

class UserInputRequest(BaseModel):
    session_id: str
    user_input: str

class Response(BaseModel):
    message: str
    next_field: Optional[str] = None
    state: Optional[dict] = None

ALL_FIELDS = [
    "mobile_number", "policy_number", "otp", "date_of_accident", "time_of_accident", "am_pm",
    "state_of_accident", "city_of_accident", "email_id", "language", "who_driver"
]

claim_keywords = {
    "english": ["claim", "intimate a claim", "file a claim", "register a claim", "report an accident", "accident registered", "accident registration"],
    "hindi": ["दावा", "दावा शुरू करना", "क्लेम", "दावा नोंदवणे", "एक्सीडेंट की रिपोर्ट करनी है", "एक्सीडेंट रिपोर्ट"],
    "marathi": ["दावा", "दावा सुरू करा", "क्लेम", "दाव्याची नोंदवही", "దావ"],
    "gujarati": ["દાવો", "દાવો શરૂ કરો", "ક્લેમ", "દાવો નોંધવો"]
}

policy_keywords = {
    "english": ["policy pdf", "policy document", "download policy", "get policy pdf"],
    "hindi": ["पॉलिसी पीडीएफ", "पॉलिसी दस्तावेज़", "पॉलिसी डाउनलोड"],
    "marathi": ["पॉलिसी पीडीएफ", "पीडीएफ"],
    "gujarati": ["પોરી", "પોલિસી પીડીએફ", "॰ डी"]
}

def initialize_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {
            "state": {key: "none" for key in ALL_FIELDS},
            "language": "english",
            "current_step": "language_selection",
            "is_registered": False,
            "flow": None,
            "try_count": 0,
            "max_retries": 3
        }
        logger.debug(f"Initialized session: {session_id}, state={sessions[session_id]}")

def infer_am_pm_from_text(user_input, language="english"):
    text = user_input.lower().strip()
    time_of_day_map = {
        "english": {"am": ["morning"], "pm": ["afternoon", "evening", "night"]},
        "hindi": {"am": ["सुबह"], "pm": ["दोपहर", "शाम", "रात"]},
        "marathi": {"am": ["सकाळ"], "pm": ["दुपारी", "सायांकाळी", "रात्री", "संध्याकाळ", "संध्याकाळी"]},
        "gujarati": {"am": ["સવાર", "સવારે", "સવારમાં"], "pm": ["બપોર", "બપોરે", "સાંજ", "સાંજે", "રાત", "રાત્રે"]}
    }
    for am_word in AM_PM_KEYWORDS.get(language, {}).get("am", []):
        if am_word in text:
            logger.debug(f"Inferred AM from AM_PM_KEYWORDS: {am_word}")
            return "AM"
    for pm_word in AM_PM_KEYWORDS.get(language, {}).get("pm", []):
        if pm_word in text:
            logger.debug(f"Inferred PM from AM_PM_KEYWORDS: {pm_word}")
            return "PM"
    time_match = re.match(r"(\d{1,2})(?::|\s*)(\d{2})?$", text)
    if time_match:
        hour = int(time_match.group(1))
        if 0 <= hour <= 11:
            logger.debug(f"Inferred AM from hour: {hour}")
            return "AM"
        elif 12 <= hour <= 23:
            logger.debug(f"Inferred PM from hour: {hour}")
            return "PM"
    logger.debug(f"No AM/PM inferred, returning 'none'")
    return "none"

def hindi_text_to_number(text):
    words = text.replace('और', '').split()
    total = 0
    current = 0
    for word in words:
        if word in HINDI_FULL_DIGIT_MAP:
            num = HINDI_FULL_DIGIT_MAP[word]
            if num >= 100:
                if current == 0:
                    current = 1
                current *= num
                total += current
                current = 0
            else:
                current += num
    total += current
    return str(total) if total else text

def normalize_spoken_digits(text, language="hindi", field=None):
    def expand_words_to_digits(words, digit_map, double_keywords):
        result = []
        skip_next = False
        for i, word in enumerate(words):
            word = word.strip().lower()
            if not word:
                continue
            if skip_next:
                skip_next = False
                continue
            if word in double_keywords and i + 1 < len(words):
                next_word = words[i + 1].strip().lower()
                if next_word in digit_map:
                    digit = str(digit_map[next_word])
                    result.append(digit)
                    result.append(digit)
                    skip_next = True
                    continue
            if word in digit_map:
                num = digit_map[word]
                result.append(str(num))
            elif word.isdigit():
                result.append(word)
            else:
                logger.debug(f"Ignored unknown word: {word}")
        return result
    words = text.strip().split()
    logger.debug(f"Normalizing spoken digits: text={text}, language={language}, words={words}")
    if language == "hindi":
        result = ''.join(expand_words_to_digits(words, HINDI_FULL_DIGIT_MAP, ["डबल", "double"]))
    elif language == "english":
        result = ''.join(expand_words_to_digits(words, ENGLISH_DIGIT_MAP, ["double"]))
    elif language == "gujarati":
        result = ''.join(expand_words_to_digits(words, GUJARATI_DIGIT_MAP, ["ડબલ", "double"]))
    elif language == "marathi":
        result = ''.join(expand_words_to_digits(words, MARATHI_DIGIT_MAP, ["डबल", "double"]))
    else:
        result = ''.join(filter(str.isdigit, text))
    logger.debug(f"Normalized spoken digits result: {result}")
    return result

def normalize_numerical_input(text, language="english", field=None):
    logger.debug(f"Normalizing numerical input: text={text}, language={language}, field={field}")
    text = to_ascii_digits(text)
    logger.debug(f"After ASCII digits: {text}")
    if field == "time_of_accident":
        text = re.sub(r'[^\d\s]', '', text).strip()
        logger.debug(f"Preserved spaces for time input: {text}")
        return text
    elif language != "english":
        text = normalize_spoken_digits(text, language, field)
    else:
        text = normalize_policy_number(text)
    logger.debug(f"After spoken digits or policy number: {text}")
    text = re.sub(r'\D+', '', text)
    logger.debug(f"Final numerical output: {text}")
    return text

def normalize_email_input(text, language="english"):
    text = unicodedata.normalize('NFKD', text)
    text = text.lower().strip()
    logger.debug(f"Original email input: {text}")
    spoken_map = {
        "एट द रेट": "@", "एटदरट": "@", "attherate": "@", "at the rate": "@", "एट": "@", "रेट": "@", "at": "@",
        "पर": "@", "वर": "@", "એટ": "@", "@": "@",
        "डॉट": ".", "dot": ".", "ડોટ": ".", "।": ".", "दॉट": ".", ".": ".",
        "underscore": "_", "अंडरस्कोर": "_", "અન્ડરસ્કોર": "_", "_": "_",
        "हायफन": "-", "હાયફન": "-", "dash": "-", "-": "-",
        "कॉम": "com", "કોમ": "com", "comma": "com", "com": "com",
        "जीमेल": "gmail", "gmail": "gmail", "જીમેલ": "gmail",
        "याहू": "yahoo", "yahoomail": "yahoo", "hotmail": "hotmail", "रेडिफ": "rediff",
        "co in": "co.in", "co dot in": "co.in", "सीओ डॉट इन": "co.in"
    }
    for spoken, actual in spoken_map.items():
        text = text.replace(spoken, actual)
    logger.debug(f"After spoken_map: {text}")
    if language != "english":
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        logger.debug(f"After transliteration: {text}")
    text = text.replace(" ", "")
    hindi_digits = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}
    for hin_digit, eng_digit in hindi_digits.items():
        text = text.replace(hin_digit, eng_digit)
    logger.debug(f"After digit replacement: {text}")
    text = re.sub(r'@+', '@', text)
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\w@.-]', '', text)
    text = text.strip('@.')
    logger.debug(f"Normalized email before regex: {text}")
    return text

MULTIPLIERS = {"double": 2, "triple": 3}
def normalize_policy_number(user_input):
    user_input = user_input.lower()
    words = re.findall(r"\w+", user_input)
    result = []
    i = 0
    while i < len(words):
        word = words[i]
        if word in MULTIPLIERS and i + 1 < len(words):
            next_word = words[i + 1]
            if next_word in ENGLISH_DIGIT_MAP:
                result.append(str(ENGLISH_DIGIT_MAP[next_word] * MULTIPLIERS[word]))
                i += 2
                continue
        if word in ENGLISH_DIGIT_MAP:
            result.append(str(ENGLISH_DIGIT_MAP[word]))
        elif word.isdigit():
            result.append(word)
        i += 1
    result = ''.join(result).strip().rstrip('.@')
    logger.debug(f"Normalized policy number: {result}")
    return result

def to_ascii_digits(text):
    table = str.maketrans(
        "०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯",
        "0123456789" * 2
    )
    return text.translate(table)

def extract_field(session_id: str, field: str, user_input: str):
    session = sessions.get(session_id)
    if not session:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    language = session["language"]
    state = session["state"]
    try_count = session["try_count"]
    max_retries = session["max_retries"]
    user_input = to_ascii_digits(user_input)
    logger.debug(f"Original user input for {field}: {user_input}")
    if user_input.strip().lower() in dont_know_phrases:
        state[field] = "none"
        session["try_count"] = 0
        logger.info(f"Extracted {field} = none")
        return Response(message=f"Extracted {field}: {field}", next_field=None, state=state)
    normalized_input = user_input
    if field in ["policy_number", "otp"]:
        normalized_input = normalize_numerical_input(user_input, language, field)
        if field == "otp" and len(normalized_input) == 6 and normalized_input.isdigit():
            state[field] = normalized_input
            session["try_count"] = 0
            logger.info(f"Extracted {field} = {normalized_input}")
            return Response(message=f"Extracted {field}: {normalized_input}", next_field=None, state=state)
        elif field == "policy_number" and len(normalized_input) == 8 and normalized_input.isdigit():
            state[field] = normalized_input
            session["try_count"] = 0
            logger.info(f"Extracted {field} = {normalized_input}")
            return Response(message=f"Extracted {field}: {normalized_input}", next_field=None, state=state)
    elif field == "email_id":
        normalized_input = normalize_email_input(user_input, language)
        logger.debug(f"Email regex check: {normalized_input}")
        if re.match(r'^[\w.-]+@[\w.-]+\.\w+$', normalized_input):
            state[field] = normalized_input
            session["try_count"] = 0
            logger.info(f"Extracted {field} = {normalized_input}")
            return Response(message=f"Extracted {field}: {normalized_input}", next_field=None, state=state)
    logger.debug(f"Normalized {field} = {normalized_input}")
    prompt = PROMPTS[field]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"{prompt.strip()}\n\nUser input: {normalized_input}\nLanguage: {language}"}],
        temperature=0
    )
    raw_response = response.choices[0].message.content.strip()
    logger.debug(f"OpenAI raw response for {field}: {raw_response}")
    if not raw_response.startswith("{"):
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            raw_response = match.group(0)
        else:
            logger.error(f"Invalid OpenAI response: {raw_response}")
            raise ValueError(f"Invalid response: {raw_response}")
    result = json.loads(raw_response)
    logger.debug(f"OpenAI parsed result for {field}: {result}")
    if field in result and result[field] not in [None, "none", "null", ""]:
        state[field] = result[field]
        session["try_count"] = 0
        logger.info(f"Extracted {field} = {result[field]}")
        return Response(message=f"Extracted {field}: {result[field]}", next_field=None, state=state)
    else:
        session["try_count"] += 1
        if field in ["policy_number", "otp"] and session["try_count"] >= max_retries:
            logger.warning(f"Could not extract {field} after {max_retries} attempts. Restarting flow.")
            initialize_session(session_id)
            session = sessions[session_id]
            return Response(
                message=LANGUAGE_STRINGS[language]["welcome"] + "\n" + LANGUAGE_STRINGS[language]["choose_language"],
                next_field="language",
                state=None
            )
        elif session["try_count"] > max_retries:
            state[field] = "none"
            session["try_count"] = 0
            logger.warning(f"Could not extract {field} after {max_retries + 1} attempts.")
            return Response(message=f"Could not extract {field} after {max_retries + 1} attempts.", next_field=None, state=state)
        logger.info(f"Prompting to repeat {field} input")
        return Response(message=LANGUAGE_STRINGS[language]["repeat_prompt"].format(field=field.replace('_', ' ')), next_field=field, state=state)

def is_mobile_registered(session_id: str, mobile: str = None):
    session = sessions.get(session_id)
    if session is None:
        initialize_session(session_id)
        session = sessions[session_id]
    language = session["language"]

    # Hardcode the mobile number as requested
    mobile = "8320441987"
    mobile = normalize_numerical_input(mobile, language, "mobile_number")
    logger.info(f"Checking registration for mobile number: {mobile}")

    api_result = get_user_policies(mobile)
    logger.debug(f"Raw API result for mobile {mobile}: {json.dumps(api_result, indent=2)}")

    # Ensure api_result['data'] is not None
    if api_result["data"] is None:
        api_result["data"] = {"CustomerData": []}

    # Patch the response if CustomerData is not nested
    if api_result["status"] == "success" and api_result["data"]:
        if isinstance(api_result["data"], list):
            # If data is a list, wrap it
            api_result["data"] = {"CustomerData": api_result["data"]}
            logger.debug(f"Wrapped CustomerData for consistency: {json.dumps(api_result, indent=2)}")
        elif isinstance(api_result["data"], dict) and "CustomerData" not in api_result["data"]:
            # If data is a dict but doesn't have CustomerData, treat as empty
            api_result["data"]["CustomerData"] = []

    # Now extract policies
    if (
        api_result["status"] == "success"
        and api_result["data"]
        and isinstance(api_result["data"].get("CustomerData"), list)
    ):
        customer_data = api_result["data"]["CustomerData"]
        logger.debug(f"CustomerData: {json.dumps(customer_data, indent=2)}")

        policies = [str(item["policyNumber"]) for item in customer_data if "policyNumber" in item]

        if not policies:
            # DEMO fallback: show two sample policies
            logger.warning(f"No policies found for mobile {mobile}. Using demo fallback.")
            customer_data = [
                {"policyNumber": "12345678", "policyType": "Motor"},
                {"policyNumber": "87654321", "policyType": "Health"}
            ]
            policies = [item["policyNumber"] for item in customer_data]
            session["policies"] = policies
            session["policy_objects"] = customer_data
            session["state"]["mobile_number"] = mobile
            session["is_registered"] = True
            policy_list_str = "\n".join([
                f"{i+1}. {item['policyNumber']} ({item.get('policyType', 'Unknown')})"
                for i, item in enumerate(customer_data)
            ])
            return True, Response(
                message=f"Which policy would you like to proceed with?\n{policy_list_str}",
                next_field="policy_number",
                state=session["state"]
            )

        session["policies"] = policies
        session["policy_objects"] = customer_data
        session["state"]["mobile_number"] = mobile
        session["is_registered"] = True

        # Show all policies for selection
        policy_list_str = "\n".join([
            f"{i+1}. {item['policyNumber']} ({item.get('policyType', 'Unknown')})"
            for i, item in enumerate(customer_data)
        ])

        logger.info(f"Extracted mobile_number = {mobile}, is_registered = True, policies = {policies}, policy_list_str = {policy_list_str}")
        return True, Response(
            message=f"Which policy would you like to proceed with?\n{policy_list_str}",
            next_field="policy_number",
            state=session["state"]
        )
    else:
        logger.error(f"API failed or no CustomerData for mobile {mobile}: {api_result}")
        session["state"]["mobile_number"] = mobile
        session["is_registered"] = False
        return False, Response(
            message=LANGUAGE_STRINGS[language]["policy_prompt"],
            next_field="policy_number",
            state=session["state"]
        )


@app.post("/start_flow", response_model=Response)
async def start_flow(request: StartFlowRequest):
    initialize_session(request.session_id)
    session = sessions[request.session_id]
    language = session["language"]
    logger.info(f"Started flow for session: {request.session_id}")
    return Response(message=LANGUAGE_STRINGS[language]["welcome"] + "\n" + LANGUAGE_STRINGS[language]["choose_language"], next_field="language", state=None)

@app.post("/submit_input", response_model=Response)
async def submit_input(request: UserInputRequest):
    session = sessions.get(request.session_id)
    if not session:
        logger.error(f"Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    mobile_number = ''.join(filter(str.isdigit, request.session_id))[:10]
    logger.info(f"Extracted mobile number from session_id: {mobile_number}")
    user_input = request.user_input.strip().lower()
    language = session["language"]
    state = session["state"]
    current_step = session["current_step"]
    logger.debug(f"Processing input: session_id={request.session_id}, current_step={current_step}, language={language}, user_input={user_input}")
    if current_step == "language_selection":
        if any(keyword in user_input for keyword in ["hindi", "हिंदी"]):
            state["language"] = language = "hindi"
        elif any(keyword in user_input for keyword in ["gujarati", "ગુજરાતી"]):
            state["language"] = language = "gujarati"
        elif any(keyword in user_input for keyword in ["marathi", "मराठी"]):
            state["language"] = language = "marathi"
        elif any(keyword in user_input for keyword in ["english"]):
            state["language"] = language = "english"
        else:
            logger.debug(f"Invalid language input: {user_input}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="language", state=state)
        session["language"] = language
        session["current_step"] = "how_help"
        return Response(message=LANGUAGE_STRINGS[language]["how_help"], next_field="how_help", state=state)
    elif current_step == "how_help":
        session["flow"] = "claim" if any(keyword in user_input for keyword in claim_keywords[language]) else "policy_pdf"
        logger.info(f"Selected flow: {session['flow']}")
        is_registered, response = is_mobile_registered(request.session_id)
        session["is_registered"] = is_registered
        session["current_step"] = "policy_number"
        return response
    elif current_step == "policy_number":
        response = extract_field(request.session_id, "policy_number", user_input)
        selected_policy = state["policy_number"]
        policy_type = None
        for obj in session.get("policy_objects", []):
            if str(obj.get("policyNumber")) == selected_policy:
                policy_type = obj.get("policyType")
                break
        if not policy_type:
            policy_type = "Motor"
        session["policy_type"] = policy_type
        if session["is_registered"] and session.get("policies") and selected_policy not in session["policies"]:
            session["current_step"] = "policy_number"
            policy_list_str = "\n".join(f"{i}. {item['policyNumber']} ({item['policyType']})" for i, item in enumerate(session["policy_objects"], start=1))
            logger.warning(f"Invalid policy number {selected_policy}. Prompting with: {policy_list_str}")
            return Response(
                message=f"Invalid policy number selected. Which policy would you like to proceed with?\n{policy_list_str}",
                next_field="policy_number",
                state=state
            )
        if policy_type == "Motor":
            if session["is_registered"]:
                session["current_step"] = "date_of_accident"
                return Response(message=LANGUAGE_STRINGS[language]["date_prompt"], next_field="date_of_accident", state=state)
            else:
                session["current_step"] = "otp"
                return Response(message=LANGUAGE_STRINGS[language]["otp_unregistered"], next_field="otp", state=state)
        elif policy_type == "Health":
            session["current_step"] = "end"
            return Response(message=LANGUAGE_STRINGS[language]["health_policy_redirect"], next_field="end", state=state)
        else:
            return response
    elif current_step == "otp":
        response = extract_field(request.session_id, "otp", user_input)
        if response.next_field is None:
            if session.get("policy_type") == "Motor":
                session["current_step"] = "date_of_accident"
                logger.info(f"OTP extracted, prompting for date_of_accident")
                return Response(message=LANGUAGE_STRINGS[language]["date_prompt"], next_field="date_of_accident", state=state)
            else:
                if session["flow"] == "claim":
                    session["current_step"] = "date_of_accident"
                    logger.info(f"OTP extracted, prompting for date_of_accident")
                    return Response(message=LANGUAGE_STRINGS[language]["date_prompt"], next_field="date_of_accident", state=state)
                else:
                    session["current_step"] = "email_id"
                    logger.info(f"OTP extracted, prompting for email_id")
                    return Response(message=LANGUAGE_STRINGS[language]["ask_email_actual"], next_field="email_id", state=state)
        return response
    elif current_step == "date_of_accident":
        response = extract_field(request.session_id, "date_of_accident", user_input)
        if response.next_field is None:
            session["current_step"] = "time_of_accident"
            logger.info(f"Date extracted, prompting for time_of_accident")
            return Response(message=LANGUAGE_STRINGS[language]["time_prompt"], next_field="time_of_accident", state=state)
        return response
    elif current_step == "time_of_accident":
        normalized_input = normalize_numerical_input(user_input, language, "time_of_accident")
        logger.debug(f"Time_of_accident normalized input: {normalized_input}")
        # Handle time inputs with spaces (e.g., "21 45")
        time_parts = normalized_input.split()
        if len(time_parts) == 2 and all(part.isdigit() for part in time_parts):
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            logger.debug(f"Parsed time parts: hour={hour}, minute={minute}")
            if 0 <= hour <= 24 and 0 <= minute <= 59:
                # Convert 24-hour to 12-hour format
                if hour == 0:
                    hour_12 = 12
                    state["am_pm"] = "AM"
                elif hour == 12:
                    hour_12 = 12
                    state["am_pm"] = "PM"
                elif hour > 12:
                    hour_12 = hour - 12
                    state["am_pm"] = "PM"
                else:
                    hour_12 = hour
                    state["am_pm"] = "AM"
                
                state["time_of_accident"] = f"{hour_12:02d}:{minute:02d}:00"
                state["am_pm"] = "PM"
                session["current_step"] = "city_of_accident"
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            elif 1 <= hour <= 12:
                state["time_of_accident"] = f"{hour:02d}:{minute:02d}:00"
                if inferred_am_pm in ["AM", "PM"]:
                    state["am_pm"] = inferred_am_pm
                    session["current_step"] = "city_of_accident"
                    return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
                else:
                    session["current_step"] = "am_pm"
                    return Response(message=LANGUAGE_STRINGS[language]["am_pm_clarify"], next_field="am_pm", state=state)
            else:
                return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="time_of_accident", state=state)
        elif re.fullmatch(r"\d{1,2}", normalized_input):
            hour = int(normalized_input)
            if 13 <= hour <= 24:
                hour_12 = hour - 12 if hour > 12 else 12
                state["time_of_accident"] = f"{hour_12:02d}:00:00"
                state["am_pm"] = "PM"
                session["current_step"] = "city_of_accident"
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            elif 1 <= hour <= 12:
                state["time_of_accident"] = f"{hour:02d}:00:00"
                if inferred_am_pm in ["AM", "PM"]:
                    state["am_pm"] = inferred_am_pm
                    session["current_step"] = "city_of_accident"
                    return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
                else:
                    session["current_step"] = "am_pm"
                    return Response(message=LANGUAGE_STRINGS[language]["am_pm_clarify"], next_field="am_pm", state=state)
            else:
                return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="time_of_accident", state=state)
        # Check for vague inputs like "at night"
        inferred_am_pm = infer_am_pm_from_text(user_input, language)
        if inferred_am_pm != "none" and not re.search(r'\d+', user_input):
            logger.debug(f"Vague input detected: {user_input}, inferred_am_pm={inferred_am_pm}")
            session["try_count"] += 1
            if session["try_count"] > session["max_retries"]:
                state["time_of_accident"] = "none"
                state["am_pm"] = "none"
                session["try_count"] = 0
                logger.warning(f"Max retries exceeded for time input: {user_input}")
                session["current_step"] = "city_of_accident"
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            return Response(
                message=LANGUAGE_STRINGS[language]["repeat_prompt"].format(field="time of accident"),
                next_field="time_of_accident",
                state=state
            )
        # Fallback to extract_field for other inputs
        logger.debug(f"Falling back to extract_field for time input: {user_input}")
        response = extract_field(request.session_id, "time_of_accident", user_input)
        if response.next_field is None:
            try:
                hour = int(state["time_of_accident"].split(":")[0])
                logger.debug(f"Extracted hour from time_of_accident: {hour}")
                # Handle 24-hour format
                if hour == 0:
                    state["am_pm"] = "AM"
                elif hour == 12:
                    state["am_pm"] = "PM"
                elif hour > 12:
                    state["am_pm"] = "PM"
                    hour_12 = hour - 12
                    minute = int(state["time_of_accident"].split(":")[1])
                    state["time_of_accident"] = f"{hour_12:02d}:{minute:02d}:00"
                else:
                    state["am_pm"] = "AM"
                logger.info(f"Extracted am_pm = {state['am_pm']}, updated time_of_accident = {state['time_of_accident']}")
                session["current_step"] = "city_of_accident"
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            except Exception as e:
                logger.error(f"Exception in time parsing: {str(e)}")
                state["am_pm"] = infer_am_pm_from_text(user_input, language)
                if state["am_pm"] == "none":
                    session["try_count"] += 1
                    if session["try_count"] > session["max_retries"]:
                        state["time_of_accident"] = "none"
                        state["am_pm"] = "none"
                        session["try_count"] = 0
                        logger.warning(f"Max retries exceeded for time input: {user_input}")
                        session["current_step"] = "city_of_accident"
                        return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
                    logger.info(f"No AM/PM detected, prompting for specific time")
                    return Response(
                        message=LANGUAGE_STRINGS[language]["repeat_prompt"].format(field="time of accident"),
                        next_field="time_of_accident",
                        state=state
                    )
                session["current_step"] = "city_of_accident"
                logger.info(f"Inferred am_pm = {state['am_pm']}, moving to city_of_accident")
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
        return response

    elif current_step == "am_pm":
        am_pm_input = user_input.strip().upper()
        if am_pm_input in ["AM", "PM"]:
            state["am_pm"] = am_pm_input
            session["current_step"] = "city_of_accident"
            logger.info(f"Extracted am_pm = {state['am_pm']}")
            return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
        else:
            logger.warning(f"Invalid AM/PM input: {am_pm_input}")
            return Response(message=LANGUAGE_STRINGS[language]["am_pm_invalid"], next_field="am_pm", state=state)
    elif current_step == "city_of_accident":
        response = extract_field(request.session_id, "city_of_accident", user_input)
        if response.next_field is None:
            session["current_step"] = "state_of_accident"
            logger.info(f"City extracted, prompting for state_of_accident")
            return Response(message=LANGUAGE_STRINGS[language]["state_prompt"], next_field="state_of_accident", state=state)
        return response
    elif current_step == "state_of_accident":
        response = extract_field(request.session_id, "state_of_accident", user_input)
        if response.next_field is None:
            if session["flow"] == "claim":
                session["current_step"] = "who_driver"
                logger.info(f"State extracted, prompting for who_driver")
                return Response(message=LANGUAGE_STRINGS[language]["driver_prompt"], next_field="who_driver", state=state)
            else:
                session["current_step"] = "end"
                logger.info(f"Claim flow completed, final state: {state}")
                return Response(
                    message=LANGUAGE_STRINGS[language]["claim_success"] + "\n" + LANGUAGE_STRINGS[language]["final_data"] + "\n" + json.dumps(state, indent=2),
                    next_field="end",
                    state=state
                )
        return response
    elif current_step == "who_driver":
        if session["flow"] != "claim":
            logger.warning(f"Who driver step accessed in non-claim flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="end", state=state)
        response = extract_field(request.session_id, "who_driver", user_input)
        if response.next_field is None:
            session["current_step"] = "end"
            logger.info(f"Driver extracted, claim flow completed, final state: {state}")
            claim_number = "<xxxxx>"
            return Response(
                message=f"Thanks for providing me with the necessary information. Your Claim has been successfully intimated with Claim number {claim_number}. Have a nice day.",
                next_field="end",
                state=state
            )
        return response
    elif current_step == "email_id":
        if session["flow"] != "policy_pdf":
            logger.warning(f"Email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="end", state=state)
        response = extract_field(request.session_id, "email_id", user_input)
        if response.next_field is None:
            session["current_step"] = "confirm_email"
            logger.info(f"Email extracted, prompting for confirmation")
            return Response(message=LANGUAGE_STRINGS[language]["email_confirm"].format(email=state["email_id"]), next_field="confirm_email", state=state)
        return response
    elif current_step == "confirm_email":
        if session["flow"] != "policy_pdf":
            logger.warning(f"Confirm email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="end", state=state)
        if user_input.startswith(("y", "हां", "हाँ", "होय", "haa", "હા")):
            session["current_step"] = "otp_email"
            logger.info(f"Email confirmed, prompting for OTP")
            return Response(message=LANGUAGE_STRINGS[language]["otp_email"], next_field="otp", state=state)
        else:
            session["current_step"] = "end"
            logger.info(f"Email not confirmed, ending flow")
            return Response(message=LANGUAGE_STRINGS[language]["no_email_no_pdf"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"], next_field="end", state=state)
    elif current_step == "otp_email":
        if session["flow"] != "policy_pdf":
            logger.warning(f"OTP email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="end", state=state)
        response = extract_field(request.session_id, "otp", user_input)
        if response.next_field is None:
            if len(str(state["otp"])) == 6 and str(state["otp"]).isdigit():
                policy_no = state["policy_number"]
                email = state["email_id"]
                api_result = insert_policy(policy_no, email)
                session["current_step"] = "end"
                logger.info(f"OTP verified, PDF sent, API result: {api_result}")
                if api_result["status"] == "success":
                    return Response(
                        message=LANGUAGE_STRINGS[language]["pdf_sent"],
                        next_field="end",
                        state=state
                    )
                else:
                    return Response(
                        message=f"Failed to send policy PDF: {api_result['message']}",
                        next_field="end",
                        state=state
                    )
            else:
                session["current_step"] = "end"
                logger.warning(f"OTP verification failed: {state['otp']}")
                return Response(
                    message=LANGUAGE_STRINGS[language]["otp_verification_failed"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"],
                    next_field="end",
                    state=state
                )
        return response
    logger.warning(f"Unexpected current_step: {current_step}")
    return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=current_step if current_step in ALL_FIELDS else "language", state=state)
