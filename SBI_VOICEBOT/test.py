from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import json
import re
import unicodedata
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from prompts import (
    POLICY_NUMBER_PROMPT, OTP_PROMPT, DATE_OF_ACCIDENT_PROMPT, TIME_OF_ACCIDENT_PROMPT,
    AM_PM_PROMPT, CITY_OF_ACCIDENT_PROMPT, STATE_OF_ACCIDENT_PROMPT,
    EMAIL_ID_PROMPT, WHO_DRIVER_PROMPT, GUJARATI_DIGIT_MAP, HINDI_FULL_DIGIT_MAP,
    HINDI_SINGLE_DIGIT_MAP, MARATHI_DIGIT_MAP, LANGUAGE_STRINGS,
    AM_PM_KEYWORDS, ENGLISH_DIGIT_MAP, dont_know_phrases, PROMPTS
)
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)  # This sends logs to stdout for Docker
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

# Pydantic models for request/response
class StartFlowRequest(BaseModel):
    session_id: str

class UserInputRequest(BaseModel):
    session_id: str
    user_input: str

class Response(BaseModel):
    message: str
    next_field: str | None = None
    state: dict | None = None

ALL_FIELDS = [
    "mobile_number", "policy_number", "otp", "date_of_accident", "time_of_accident", "am_pm",
    "state_of_accident", "city_of_accident", "email_id", "language", "who_driver"
]

claim_keywords = {
    "english": ["claim", "intimate a claim", "file a claim", "register a claim", "report an accident", "accident registered", "accident registration"],
    "hindi": ["दावा", "दावा शुरू करना", "क्लेम", "दावा नोंदवणे", "एक्सीडेंट की रिपोर्ट करनी है", "एक्सीडेंट रिपोर्ट", "दुर्घटना की रिपोर्ट", "दुर्घटना दर्ज", "एक्सीडेंट दर्ज"],
    "marathi": ["दावा", "दावा सुरू करा", "क्लेम", "दाव्याची नोंदवही", "दावा नोंदवणे", "अपघाताची नोंद", "अपघात रिपोर्ट", "अपघाताची माहिती", "हक्क सांगणे"],
    "gujarati": ["દાવો", "દાવો શરૂ કરો", "ક્લેમ", "દાવો નોંધવો", "અપઘાત નોંધવો", "અપઘાત રિપોર્ટ", "અપઘાતની જાણ"]
}

policy_keywords = {
    "english": ["policy pdf", "policy document", "download policy", "get policy pdf"],
    "hindi": ["पॉलिसी पीडीएफ", "पॉलिसी दस्तावेज़", "पॉलिसी डाउनलोड"],
    "marathi": ["पॉलिसी पीडीएफ", "पीडीएफ", "पॉलिसी", "डाऊनलोड", "पॉलिसी दस्तऐवज", "પોલિસી ડાઉનલોડ", "माझ्या पॉलिसीची पीडीएफ", "माझी पॉलिसी पीडीएफ", "माझ्या पॉलिसीचा दस्तऐवज"],
    "gujarati": ["પોલિસી પીડીએફ", "પોલિસી દસ્તાવેજ", "પોલિસી ડાઉનલોડ", "પી", "પોલિી"]
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
        logger.debug(f"Initialized session: {session_id}, state: {sessions[session_id]}")

def infer_am_pm_from_text(user_input, language="english"):
    text = user_input.lower().strip()
    time_of_day_map = {
        "english": {"am": ["morning"], "pm": ["afternoon", "evening", "night"]},
        "hindi": {"am": ["सुबह"], "pm": ["दोपहर", "शाम", "रात"]},
        "marathi": {"am": ["सकाळ"], "pm": ["दुपारी", "सायांकाळी", "रात्री", "संध्याकाळ", "संध्याकाळी"]},
        "gujarati": {"am": ["સવાર", "સવારે", "સવારમાં"], "pm": ["બપોર", "બપોરે", "સાંજ", "સાંજે", "રાત", "રાત્રે"]}
    }

    # Check explicit AM/PM keywords
    for am_word in AM_PM_KEYWORDS.get(language, {}).get("am", []):
        if am_word in text:
            logger.debug(f"Inferred AM from AM_PM_KEYWORDS: {am_word}")
            return "AM"
    for pm_word in AM_PM_KEYWORDS.get(language, {}).get("pm", []):
        if pm_word in text:
            logger.debug(f"Inferred PM from AM_PM_KEYWORDS: {pm_word}")
            return "PM"

    # Check numerical time in "HH MM", "HH:MM", or "HH" format
    time_match = re.match(r"(\d{1,2})(?::|\s*)(\d{2})?$", text)
    if time_match:
        hour = int(time_match.group(1))
        if 0 <= hour <= 11:
            logger.debug(f"Inferred AM from hour: {hour}")
            return "AM"
        elif 12 <= hour <= 23:
            logger.debug(f"Inferred PM from hour: {hour}")
            return "PM"

    # Return "none" for vague inputs like "at night"
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
        # Preserve spaces for time inputs like "21 45"
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

def normalize_email_input(text):
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

    text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    logger.debug(f"After transliteration: {text}")

    hindi_digits = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}
    for hin_digit, eng_digit in hindi_digits.items():
        text = text.replace(hin_digit, eng_digit)
    logger.debug(f"After digit replacement: {text}")

    text = re.sub(r'@+', '@', text)
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^\w@.-]', '', text)
    text = text.strip('@.')
    logger.debug(f"Normalized email: {text}")
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
        return Response(message=f"Extracted {field}: none", next_field=None, state=state)

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
        normalized_input = normalize_email_input(user_input)
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
            initialize_session(session_id)  # Reset session
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

def is_mobile_registered(session_id: str, mobile: str):
    session = sessions.get(session_id)
    language = session["language"]
    mobile = normalize_numerical_input(mobile, language, "mobile_number")
    
    if re.fullmatch(r"\d{10}", mobile):
        session["state"]["mobile_number"] = mobile
        session["is_registered"] = mobile.endswith("78")
        logger.info(f"Extracted mobile_number = {mobile}, is_registered = {session['is_registered']}")
        return session["is_registered"], Response(
            message=LANGUAGE_STRINGS[language]["mobile_registered"] if session["is_registered"] else LANGUAGE_STRINGS[language]["mobile_unregistered"],
            next_field=None,
            state=session["state"]
        )
    else:
        logger.info(f"Invalid mobile number: {mobile}")
        return None, Response(message=LANGUAGE_STRINGS[language]["invalid_mobile"], next_field=None, state=session["state"])

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

    # Extract first 10 digits from session_id as mobile_number
    mobile_number = request.session_id[:10]
    logger.info(f"Extracted mobile number: {mobile_number}")

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
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="language", state=None)
        
        session["language"] = language
        session["current_step"] = "how_help"
        logger.info(f"Language selected: {language}")
        return Response(message=LANGUAGE_STRINGS[language]["continue_language"] + "\n" + LANGUAGE_STRINGS[language]["how_help"], next_field="intent", state=None)

    elif current_step == "how_help":
        if any(keyword in user_input for keyword in claim_keywords[language]):
            session["flow"] = "claim"
            session["current_step"] = "mobile_number"
            logger.info(f"Selected claim flow")
            # Process mobile number automatically
            is_registered, response = is_mobile_registered(request.session_id, mobile_number)
            if response.next_field is None:
                session["current_step"] = "policy_number"
                if is_registered:
                    message = LANGUAGE_STRINGS[language]["policy_list"] + "\n" + LANGUAGE_STRINGS[language]["policy_prompt"]
                else:
                    message = LANGUAGE_STRINGS[language]["policy_number_prompt"]
                logger.info(f"Mobile registered: {is_registered}, prompting for policy_number")
                return Response(message=message, next_field="policy_number", state=state)
            else:
                # Invalid mobile number, end flow
                session["current_step"] = "end"
                logger.warning(f"Invalid mobile number extracted: {mobile_number}")
                return Response(message=LANGUAGE_STRINGS[language]["invalid_mobile"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"], next_field=None, state=state)
        elif any(keyword in user_input for keyword in policy_keywords[language]):
            session["flow"] = "policy_pdf"
            session["current_step"] = "mobile_number"
            logger.info(f"Selected policy_pdf flow")
            # Process mobile number automatically
            is_registered, response = is_mobile_registered(request.session_id, mobile_number)
            if response.next_field is None:
                policies = ["12345678", "87654321"]
                message = LANGUAGE_STRINGS[language]["policy_list"].format(policy1=policies[0], policy2=policies[1]) + "\n" + LANGUAGE_STRINGS[language]["policy_prompt"]
                if is_registered:
                    session["current_step"] = "policy_number"
                    logger.info(f"Mobile registered, prompting for policy_number in policy_pdf flow")
                    return Response(message=message, next_field="policy_number", state=state)
                else:
                    session["current_step"] = "otp"
                    logger.info(f"Mobile unregistered, prompting for OTP in policy_pdf flow")
                    return Response(message=LANGUAGE_STRINGS[language]["otp_unregistered"], next_field="otp", state=state)
            else:
                # Invalid mobile number, end flow
                session["current_step"] = "end"
                logger.warning(f"Invalid mobile number extracted: {mobile_number}")
                return Response(message=LANGUAGE_STRINGS[language]["invalid_mobile"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"], next_field=None, state=state)
        else:
            logger.debug(f"Invalid intent input: {user_input}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="intent", state=state)

    elif current_step == "policy_number":
        response = extract_field(request.session_id, "policy_number", user_input)
        if state["policy_number"].endswith("4321"):
            session["current_step"] = "end"
            logger.info(f"Policy ends with 4321, redirecting")
            return Response(message=LANGUAGE_STRINGS[language]["health_policy_redirect"], next_field=None, state=state)
        if response.next_field is None:
            if session["flow"] =="claim":
                session["current_step"] = "otp"
                message = LANGUAGE_STRINGS[language]["fetch_policy"] + "\n" + (LANGUAGE_STRINGS[language]["otp_registered"] if session["is_registered"] else LANGUAGE_STRINGS[language]["otp_unregistered"])
                logger.info(f"Policy extracted, prompting for OTP in claim flow")
                return Response(message=message, next_field="otp", state=state)
            else:  # policy_pdf
                policies = ["12345678", "87654321"]
                if state["policy_number"] not in policies:
                    session["current_step"] = "end"
                    logger.warning(f"Invalid policy number: {state['policy_number']}")
                    return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=None, state=state)
                session["current_step"] = "otp"
                logger.info(f"Policy extracted, prompting for OTP in policy_pdf flow")
                return Response(message=LANGUAGE_STRINGS[language]["otp_unregistered"], next_field="otp", state=state)
        return response

    elif current_step == "otp":
        response = extract_field(request.session_id, "otp", user_input)
        if response.next_field is None:
            if session["flow"] == "claim":
                session["current_step"] = "date_of_accident"
                logger.info(f"OTP extracted, prompting for date_of_accident")
                return Response(message=LANGUAGE_STRINGS[language]["date_prompt"], next_field="date_of_accident", state=state)
            else:  # policy_pdf
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
                session["current_step"] = "city_of_accident"
                logger.info(f"Extracted time_of_accident = {state['time_of_accident']}, am_pm = {state['am_pm']}")
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            else:
                logger.warning(f"Invalid time input: hour={hour}, minute={minute}")
                return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field="time_of_accident", state=state)
        # Handle single number input (e.g., "21")
        elif re.fullmatch(r"\d{1,2}", normalized_input):
            hour = int(normalized_input)
            logger.debug(f"Parsed single hour: {hour}")
            if 0 <= hour <= 24:
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
                
                state["time_of_accident"] = f"{hour_12:02d}:00:00"
                session["current_step"] = "city_of_accident"
                logger.info(f"Extracted time_of_accident = {state['time_of_accident']}, am_pm = {state['am_pm']}")
                return Response(message=LANGUAGE_STRINGS[language]["city_prompt"], next_field="city_of_accident", state=state)
            else:
                logger.warning(f"Invalid hour: {hour}")
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
                    next_field=None,
                    state=state
                )
        return response

    elif current_step == "who_driver":
        if session["flow"] != "claim":
            logger.warning(f"Who driver step accessed in non-claim flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=None, state=state)
        response = extract_field(request.session_id, "who_driver", user_input)
        if response.next_field is None:
            session["current_step"] = "end"
            logger.info(f"Driver extracted, claim flow completed, final state: {state}")
            return Response(
                message=LANGUAGE_STRINGS[language]["claim_success"] + "\n" + LANGUAGE_STRINGS[language]["final_data"] + "\n" + json.dumps(state, indent=2),
                next_field=None,
                state=state
            )
        return response

    elif current_step == "email_id":
        if session["flow"] != "policy_pdf":
            logger.warning(f"Email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=None, state=state)
        response = extract_field(request.session_id, "email_id", user_input)
        if response.next_field is None:
            session["current_step"] = "confirm_email"
            logger.info(f"Email extracted, prompting for confirmation")
            return Response(message=LANGUAGE_STRINGS[language]["email_confirm"].format(email=state["email_id"]), next_field="confirm_email", state=state)
        return response

    elif current_step == "confirm_email":
        if session["flow"] != "policy_pdf":
            logger.warning(f"Confirm email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=None, state=state)
        if user_input.startswith(("y", "हां", "हाँ", "होय", "haa", "હા")):
            session["current_step"] = "otp_email"
            logger.info(f"Email confirmed, prompting for OTP")
            return Response(message=LANGUAGE_STRINGS[language]["otp_email"], next_field="otp", state=state)
        else:
            session["current_step"] = "end"
            logger.info(f"Email not confirmed, ending flow")
            return Response(message=LANGUAGE_STRINGS[language]["no_email_no_pdf"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"], next_field=None, state=state)

    elif current_step == "otp_email":
        if session["flow"] != "policy_pdf":
            logger.warning(f"OTP email step accessed in non-policy_pdf flow: {session['flow']}")
            return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=None, state=state)
        response = extract_field(request.session_id, "otp", user_input)
        if response.next_field is None:
            if len(str(state["otp"])) == 6 and str(state["otp"]).isdigit():
                session["current_step"] = "end"
                logger.info(f"OTP verified, PDF sent")
                return Response(
                    message=LANGUAGE_STRINGS[language]["pdf_sent"],
                    next_field=None,
                    state=state
                )
            else:
                session["current_step"] = "end"
                logger.warning(f"OTP verification failed: {state['otp']}")
                return Response(
                    message=LANGUAGE_STRINGS[language]["otp_verification_failed"] + "\n" + LANGUAGE_STRINGS[language]["end_flow"],
                    next_field=None,
                    state=state
                )
        return response

    logger.warning(f"Unexpected current_step: {current_step}")
    return Response(message=LANGUAGE_STRINGS[language]["invalid_input"], next_field=current_step if current_step in ALL_FIELDS else "language", state=state)
