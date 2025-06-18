from datetime import datetime

today_str = datetime.today().strftime("%d %B %Y")
now_str = datetime.now().strftime("%H:%M:%S")

POLICY_NUMBER_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **policy_number** from the user input below.
Return a JSON with exactly this field: {{ "policy_number": "<value>" }} or {{ "policy_number": null }}.

### Field: policy_number
- Must be an 8-digit number (e.g., "12345678") or a 4-digit suffix (e.g., "1234") if contextually stated (e.g., "ends with 1234").
- Accept spoken digits in English (e.g., "one two three four"), Hindi (e.g., "एक दो तीन चार"), Marathi (e.g., "एक दोन तीन चार"), or Gujarati (e.g., "એક બે ત્રણ ચાર").
- Accept mixed spoken and numeral inputs (e.g., "one 2 three 4" → "1234", "sixty 20 1 2" → "602012").
- Accept multipliers like "double" or "triple" (e.g., "double one" → "11", "triple two" → "222").
- Accept chunked inputs (e.g., "100 00001" → "10000001").
- If exactly 4 digits are provided (e.g., "શૂન્ય શૂન્ય શૂન્ય પાંચ" → "0005"), accept as policy_number only if explicitly stated as policy number.
- Concatenate all digits in order, ignoring non-digit separators (e.g., spaces, hyphens).
- Do not accept invalid lengths or non-numeric inputs.
- Examples:
  - English: "policy ending with one two three four" → {{ "policy_number": "1234" }}
  - English: "sixty 20 1 2" → {{ "policy_number": "602012" }}
  - English: "double one 2 three 4 five 6 seven 8" → {{ "policy_number": "11234567" }}
  - Hindi: "पॉलिसी नंबर एक दो तीन चार" → {{ "policy_number": "1234" }}
  - Hindi: "पॉलिसी नंबर एक 1 तीन 4 पांच 6 सात 8" → {{ "policy_number": "11345678" }}
  - Marathi: "पॉलिसी नंबर एक दोन तीन चार" → {{ "policy_number": "1234" }}
  - Gujarati: "પોલિસી નંબર એક બે ત્રણ ચાર" → {{ "policy_number": "1234" }}
  - Gujarati: "શૂન્ય શૂન્ય શૂન્ય પાંચ" → {{ "policy_number": "0005" }}
  - Chunked: "100 00001" → {{ "policy_number": "10000001" }}
"""

OTP_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **otp** from the user input below.
Return a JSON with exactly this field: {{ "otp": "<value>" }} or {{ "otp": null }}.

### Field: otp
- Must be exactly 6 digits (e.g., "123456").
- Accept spoken digits in English (e.g., "one two three four five six"), Hindi (e.g., "एक दो तीन चार पांच छह"), Marathi (e.g., "एक दोन तीन चार पाच सहा"), or Gujarati (e.g., "એક બે ત્રણ ચાર પાંચ છ").
- Accept mixed spoken and numeral inputs (e.g., "sixty 20 1 2" → "602012", "one 2 three 4 five 6" → "123456").
- Accept multipliers like "double" or "triple" (e.g., "double one" → "11", "triple two" → "222").
- Accept formats like "123-456" or "123 456" by concatenating digits.
- Concatenate all digits in order, ignoring non-digit separators (e.g., spaces, hyphens).
- If the input is spoken in Hindi/Marathi/Gujarati words (e.g., 'पाँच लाख सड़सठ हज़ार आठ सौ तैंतालीस'), convert to digits (e.g., '567843').
- Do not accept inputs with fewer or more than 6 digits.
- Examples:
  - English: "one two three four five six" → {{ "otp": "123456" }}
  - English: "sixty 20 1 2" → {{ "otp": "602012" }}
  - English: "double one 2 three 4 five" → {{ "otp": "112345" }}
  - Hindi: "एक दो तीन चार पांच छह" → {{ "otp": "123456" }}
  - Hindi: "एक 2 तीन 4 पांच 6" → {{ "otp": "123456" }}
  - Marathi: "एक दोन तीन चार पाच सहा" → {{ "otp": "123456" }}
  - Gujarati: "એક બે ત્રણ ચાર પાંચ છ" → {{ "otp": "123456" }}
  - Formatted: "123-456" → {{ "otp": "123456" }}
"""

MOBILE_NUMBER_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **mobile_number** from the user input below.
Return a JSON with exactly this field: {{ "mobile_number": "<value>" }} or {{ "mobile_number": null }}.

### Field: mobile_number
- Must be exactly 10 digits (e.g., "1234567890").
- Accept spoken digits in English (e.g., "one two three four five six seven eight nine zero"), Hindi (e.g., "एक दो तीन चार पांच छह सात आठ नौ शून्य"), Marathi (e.g., "एक दोन तीन चार पाच सहा सात आठ नऊ शून्य"), or Gujarati (e.g., "એક બે ત્રણ ચાર પાંચ છ સાત આઠ નવ શૂન્ય").
- Accept mixed spoken and numeral inputs (e.g., "one 2 three 4 five 6 seven 8 nine 0" → "1234567890").
- Accept multipliers like "double" or "triple" (e.g., "double one" → "11", "triple two" → "222").
- Accept chunked inputs (e.g., "123 456 7890" → "1234567890").
- Concatenate all digits in order, ignoring non-digit separators (e.g., spaces, hyphens).
- Do not accept inputs with fewer or more than 10 digits.
- Examples:
  - English: "one two three four five six seven eight nine zero" → {{ "mobile_number": "1234567890" }}
  - English: "double one 2 three 4 five 6 seven 8 nine" → {{ "mobile_number": "1123456789" }}
  - Hindi: "एक दो तीन चार पांच छह सात आठ नौ शून्य" → {{ "mobile_number": "1234567890" }}
  - Hindi: "एक 2 तीन 4 पांच 6 सात 8 नौ 0" → {{ "mobile_number": "1234567890" }}
  - Marathi: "एक दोन तीन चार पाच सहा सात आठ नऊ शून्य" → {{ "mobile_number": "1234567890" }}
  - Gujarati: "એક બે ત્રણ ચાર પાંચ છ સાત આઠ નવ શૂન્ય" → {{ "mobile_number": "1234567890" }}
  - Chunked: "123 456 7890" → {{ "mobile_number": "1234567890" }}
"""

DATE_OF_ACCIDENT_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **date_of_accident** from the user input below.
Return a JSON with exactly this field in DD/MM/YYYY format: {{ "date_of_accident": "<value>" }} or {{ "date_of_accident": null }}.

### Field: date_of_accident
- Accept absolute dates (e.g., "16 December 2024", "16/12/2024").
- Accept relative dates (e.g., "5 days ago", "yesterday").
- Accept spoken forms in English (e.g., "sixteenth December twenty twenty-four"), Hindi (e.g., "सोलह दिसंबर दो हज़ार चौबीस"), Marathi (e.g., "सोळा डिसेंबर दोन हजार चोवीस"), or Gujarati (e.g., "સોળ ડિસેમ્બર બે હજાર ચોવીસ").
- Convert multilingual relative terms:
  - English: "yesterday" → previous day
  - Hindi: "कल" → previous day, "आज" → today, "परसों" → day before yesterday
  - Marathi: "काल" → yesterday, "आज" → today, "परवा" → day before yesterday
  - Gujarati: "ગઈકાલ" → yesterday, "આજ" → today, "પરમ દિવસ" → day before yesterday
- Examples:
  - English: "sixteen December twenty twenty-four" → {{ "date_of_accident": "16/12/2024" }}
  - Hindi: "सोलह दिसंबर दो हज़ार चौबीस" → {{ "date_of_accident": "16/12/2024" }}
  - Marathi: "सोळा डिसेंबर दोन हजार चोवीस" → {{ "date_of_accident": "16/12/2024" }}
  - Gujarati: "સોળ ડિસેમ્બર બે હજાર ચોવીસ" → {{ "date_of_accident": "16/12/2024" }}
"""

TIME_OF_ACCIDENT_PROMPT = f"""Today's date is {today_str} and current time is {now_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract both fields: **time_of_accident** and **am_pm** from the user input.
If the input refers to a time like "an hour ago", subtract it from {now_str} and format accordingly.
Return a JSON with both fields.

### Field: time_of_accident
- Return in "HH:MM:00" format (12-hour).
- Accept standard and compressed formats like "5 PM", "530 evening", "515".
- Accept formats like "HH:MM" → "HH:MM:00".
- Accept spoken inputs like "चार बजे", "सुबह सात बजे", etc.
- If input is 2 or 3 digits (e.g., "515"), parse as HHMM → "05:15:00".
- Accept 24-hour format like "16" and convert to 12-hour with am_pm.
- If user says AM/PM or context like "morning", "evening", apply that to "am_pm".
- If only a number from 0–11 is given with no time context, omit am_pm.

### Field: am_pm
- Detect using time context:
  - "AM", "PM"
  - "morning", "सुबह", "સવાર" → AM
  - "afternoon" → AM if time < 12
  - "evening", "night", "शाम", "দোপাহার", "সং", "રાત્રી" → PM

### Examples:
- "530 evening" → {{ "time_of_accident": "05:30:00", "am_pm": "PM" }}
- "सुबह दस बजे" → {{ "time_of_accident": "10:00:00", "am_pm": "AM" }}
- "दोपहर के ग्यारह बजे" → {{ "time_of_accident": "11:00:00", "am_pm": "AM" }}
- "13" → {{ "time_of_accident": "01:00:00", "am_pm": "PM" }}
- "4" → {{ "time_of_accident": "04:00:00", "am_pm": null }}
"""

AM_PM_PROMPT = f"""You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **am_pm** from the user input.
Return a JSON with exactly this field: {{ "am_pm": "<value>" }} or {{ "am_pm": null }}.

### Field: am_pm
- Explicit: AM/PM, morning/evening.
- Infer from 24-hour time: 13:00 → PM, 00:30 → AM.
- Examples:
  - "AM" → {{ "am_pm": "AM" }}
  - "evening" → {{ "am_pm": "PM" }}
  - "13:00" → {{ "am_pm": "PM" }}
"""

STATE_OF_ACCIDENT_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **state_of_accident** from the user input.
Return a JSON with exactly this field: {{ "state_of_accident": "<value>" }} or {{ "state_of_accident": null }}.

### Field: state_of_accident
- Capitalize state name (e.g., "Maharashtra").
- Accept names in English, Hindi (e.g., "महाराष्ट्र"), Marathi (e.g., "महाराष्ट्र"), or Gujarati (e.g., "મહારાષ્ટ્ર").
- Do not infer from city.
- Examples:
  - English: "Maharashtra" → {{ "state_of_accident": "Maharashtra" }}
  - Hindi: "महाराष्ट्र" → {{ "state_of_accident": "Maharashtra" }}
  - Marathi: "महाराष्ट्र" → {{ "state_of_accident": "Maharashtra" }}
  - Gujarati: "મહારાષ્ટ્ર" → {{ "state_of_accident": "Maharashtra" }}
"""

CITY_OF_ACCIDENT_PROMPT = f"""Today's date is {today_str}.
You are a voicebot post-processor for SBI General Insurance.
Extract only the field: **city_of_accident** from the user input.
Return a JSON with exactly this field: {{ "city_of_accident": "<value>" }} or {{ "city_of_accident": null }}.

### Field: city_of_accident
- Capitalize city name (e.g., "Mumbai").
- Accept names in English, Hindi (e.g., "मुंबई"), Marathi (e.g., "मुंबई"), or Gujarati (e.g., "મુંબઈ").
- Examples:
  - English: "Mumbai" → {{ "city_of_accident": "Mumbai" }}
  - Hindi: "मुंबई" → {{ "city_of_accident": "Mumbai" }}
  - Marathi: "मुंबई" → {{ "city_of_accident": "Mumbai" }}
  - Gujarati: "મુંબઈ" → {{ "city_of_accident": "Mumbai" }}
"""

WHO_DRIVER_PROMPT = f"""You are a multilingual voicebot post-processor for SBI General Insurance.
Extract only the field: **who_driver** from the user input.
Return a JSON with exactly this field: {{ "who_driver": "<value>" }}.

### Valid values for who_driver:
- "owner" → if the user says they were driving, e.g.:
  - English: "I was driving", "me", "myself", "I drove"
  - Hindi: "मैं चला रहा था", "मैं", "मैंने चलाई", "मेरे द्वारा"
  - Marathi: "मी गाडी चालवत होतो", "मी", "माझ्याने", "मी चालवली"
  - Gujarati: "હું ચલાવતો હતો", "હું", "મેં ચલાવ્યું"
- "driver" → if a hired driver, chauffeur, or professional driver is mentioned, e.g.:
  - English: "driver", "chauffeur", "hired driver", "the driver"
  - Hindi: "ड्राइवर", "चालक", "मेरा ड्राइवर", "पेशेवर ड्राइवर"
  - Marathi: "ड्रायव्हर", "चालक", "माझा ड्रायव्हर", "भाड्याचा ड्रायवर"
  - Gujarati: "ડ્રાઈવર", "ચાલક", "મારો ડ્રાઈવર", "ભાડાનો ડ્રાઈવર"
- "no one" → if:
  - The user says the car was not being driven (e.g., "car was parked", "गाड़ी खड़ी थी", "गाडी थक थक", "કાર પાર્ક હતી").
  - The user says they don’t know who was driving (e.g., "I don't know", "मुझे नहीं पता", "मला माहीत नाही", "મને ખબર નથી").
  - The user mentions a family member or other individual not explicitly identified as a hired driver (e.g., "my mother", "मेरी माँ", "माझी आई", "મારી મા", "Rajesh", "brother").
  - Nothing specific about who was driving is mentioned.
- Examples:
  - "ड्राइवर" → {{ "who_driver": "driver" }}
  - "I was driving" → {{ "who_driver": "owner" }}
  - "गाड़ी खड़ी थी" → {{ "who_driver": "no one" }}
  - "मुझे नहीं पता" → {{ "who_driver": "no one" }}
  - "my mother" → {{ "who_driver": "no one" }}
"""

EMAIL_ID_PROMPT = f"""You are an intelligent assistant for SBI General Insurance.
Extract only the **actual email address** from the user input using LLM understanding.
Do not perform fallback logic, regex, or postprocessing. Extract based only on user's spoken or written format.

### Return format:
{{ "email_id": "<value>" }} or {{ "email_id": null }}

### Accept:
- Full spoken forms (e.g., "vinay underscore rathod at the rate yahoo dot co dot in" → {{ "email_id": "vinay_rathod@yahoo.co.in" }}).
- Partially written/spoken forms (e.g., "shah dot amit at rediff dot com" → {{ "email_id": "shah.amit@rediff.com" }}).
- Transliterated Indian languages (Gujarati, Hindi, etc.).
- Examples:
  - "vinay dot rathod at gmail dot com" → {{ "email_id": "vinay.rathod@gmail.com" }}
  - "शाह डॉट अमित एट रेडिफ डॉट कॉम" → {{ "email_id": "shah.amit@rediff.com" }}
"""

AM_PM_KEYWORDS = {
    "english": {
        "am": ["am", "morning"],
        "pm": ["pm", "afternoon", "evening", "night"]
    },
    "hindi": {
        "am": ["am", "सुबह", "प्रभात"],
        "pm": ["pm", "दोपहर", "शाम", "रात"]
    },
    "marathi": {
        "am": ["am", "सकाळ", "सकाळी"],
        "pm": ["pm", "दुपारी", "सायंकाळी", "रात्री"]
    },
    "gujarati": {
        "am": ["am", "સવાર", "સવારે"],
        "pm": ["pm", "બપોર", "સાંજ", "રાત", "રાત્રે"]
    }
}

dont_know_phrases = [
    "i don't know", "i dont know", "dont know", "मुझे नहीं पता", "मला माहीत नाही", 
    "माहीत नाही", "मला माहिती नाही", "माहिती नाही", "मुझे नही पता", 
    "मला खबर नाही", "खबर नाही", "मने खबर नथी", "મને ખબર નથી", 
    "ખબર નથી", "not sure", "no idea", "कोई जानकारी नहीं", 
    "कोई मालूम नहीं", "मालूम नहीं", "काही माहीत नाही", "काही खबर नाही", 
    "काही माहिती नाही"
]

HINDI_FULL_DIGIT_MAP = {
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, 
    "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7, 
    "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, 
    "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "सोलह": 16, 
    "सत्रह": 17, "अठारह": 18, "उन्नीस": 19, "बीस": 20, 
    "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24, 
    "पच्चीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28, 
    "उनतीस": 29, "तीस": 30, "इकतीस": 31, "बत्तीस": 32, 
    "तैंतीस": 33, "चौतीस": 34, "पैंतीस": 35, "छत्तीस": 36, 
    "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39, "चालीस": 40, 
    "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44, 
    "पैंतालीस": 45, "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48, 
    "उनचास": 49, "पचास": 50, "इक्यावन": 51, "बावन": 52, 
    "तिरपन": 53, "चौवन": 54, "पचपन": 55, "छप्पन": 56, 
    "सत्तावन": 57, "अट्ठावन": 58, "उनसठ": 59, "साठ": 60, 
    "इकसठ": 61, "बासठ": 62, "तिरसठ": 63, "चौसठ": 64, 
    "पैंसठ": 65, "छियासठ": 66, "सड़सठ": 67, "अड़सठ": 68, 
    "उनहत्तर": 69, "सत्तर": 70, "इकहत्तर": 71, "बाहत्तर": 72, 
    "तिहत्तर": 73, "चौहत्तर": 74, "पचहत्तर": 75, "छहत्तर": 76, 
    "सतहत्तर": 77, "अठहत्तर": 78, "उन्यासी": 79, "अस्सी": 80, 
    "इक्यासी": 81, "बयासी": 82, "तिरासी": 83, "चौरासी": 84, 
    "पचासी": 85, "छियासी": 86, "सतासी": 87, "अट्ठासी": 88, 
    "नवासी": 89, "नब्बे": 90, "इक्यानवे": 91, "बानवे": 92, 
    "तिरानवे": 93, "चौरानवे": 94, "पचानवे": 95, "छियानवे": 96, 
    "सतानवे": 97, "अट्ठानवे": 98, "निन्यानवे": 99,
    "सौ": 100, "हज़ार": 1000, "लाख": 100000, "करोड़": 10000000
}

HINDI_SINGLE_DIGIT_MAP = {
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4,
    "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9
}

GUJARATI_DIGIT_MAP = {
    "શૂન્ય": 0, "એક": 1, "બે": 2, "ત્રણ": 3, "ચાર": 4,
    "પાંચ": 5, "છ": 6, "સાત": 7, "આઠ": 8, "નવ": 9,
    "દસ": 10, "અગિયાર": 11, "બાર": 12, "તેર": 13,
    "ચૌદ": 14, "પંદર": 15, "સોળ": 16, "સત્તર": 17,
    "અઢાર": 18, "ઓગણીસ": 19, "વીસ": 20, "એકવીસ": 21,
    "બાવીસ": 22, "તેવીસ": 23, "ચોવીસ": 24, "પચ્ચીસ": 25,
    "છવીસ": 26, "સત્તાવીસ": 27, "અઠ્ઠાવીસ": 28, "ઓગણત્રીસ": 29,
    "ત્રીસ": 30, "એકત્રીસ": 31, "બત્રીસ": 32, "તેત્રીસ": 33,
    "ચોત્રીસ": 34, "પાંત્રીસ": 35, "છત્રીસ": 36, "સાડત્રીસ": 37,
    "અડત્રીસ": 38, "ઓગણચાલીસ": 39, "ચાલીસ": 40, "એકચાલીસ": 41,
    "બે ચાલીસ": 42, "તેતાલીસ": 43, "ચોરીસ": 44, "પિસ્તાલીસ": 45,
    "છેતાલીસ": 46, "સાડે ચાલીસ": 47, "અડતાલીસ": 48, "ઓગણપચાસ": 49,
    "પચાસ": 50
}

MARATHI_DIGIT_MAP = {
    "शून्य": 0, "एक": 1, "दोन": 2, "तीन": 3, "चार": 4,
    "पाच": 5, "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9,
    "दहा": 10, "अकरा": 11, "बारा": 12, "तेरा": 13,
    "चौदा": 14, "पंधरा": 15, "सोळा": 16, "सतरा": 17,
    "अठरा": 18, "एकोणीस": 19, "वीस": 20
}

ENGLISH_DIGIT_MAP = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90
}

LANGUAGE_STRINGS = {
    "english": {
        "welcome": "🤖 Hi, Welcome to SBI General Insurance.",
        "choose_language": "Which language would you like to continue in? Hindi, English, Marathi, or Gujarati?",
        "continue_language": "You can continue in English.",
        "how_help": "How may I assist you today?",
        "claim_prompt": "I can assist with claim intimation or policy PDF retrieval. Please say something like 'I want to intimate a claim' or 'I want to download my policy PDF.'",
        "mobile_prompt": "Please provide your mobile number.",
        "mobile_registered": "Thank you. This number is registered with us.",
        "mobile_unregistered": "This number does not appear to be registered with us.",
        "policy_list": "You have the following policies:\n- Policy 12345678\n- Policy 87654321",
        "policy_prompt": "Which policy would you like to proceed with?",
        "policy_number_prompt": "Please provide your policy number.",
        "fetch_policy": "Fetching policy details, please wait...",
        "otp_registered": "An OTP has been sent to your registered mobile. Please provide the 6-digit OTP.",
        "otp_unregistered": "An OTP has been sent to your mobile number. Please provide the 6-digit OTP.",
        "date_prompt": "Please tell me the date of the accident.",
        "time_prompt": "Please tell me the time of the accident.",
        "am_pm_prompt": "Please specify AM or PM.",
        "city_prompt": "Please tell me the city where the accident occurred.",
        "state_prompt": "Please tell me the state where the accident occurred.",
        "driver_prompt": "Thank you. Who was driving the car?",
        "email_prompt": "Do you have an email ID to share? (yes/no)",
        "ask_email_actual": "Please provide your email address.",
        "email_confirm": "Please confirm, is this your email: {email}? (yes/no)",
        "claim_success": "✅ Your claim has been successfully intimated.",
        "final_data": "📄 Final structured data:",
        "policy_pdf_flow": "Let's help you download your policy PDF.",
        "policy_pdf_sent": "Sure, we have shared the Policy Document via your registered email ID. Can I help you with anything else?",
        "send_pdf_email_prompt": "Would you like to receive your policy PDF on your registered email? (yes/no)",
        "otp_email": "We have sent an OTP to your email. Please enter the OTP.",
        "otp_verification_success": "Your OTP is successfully verified and registered email has been successfully updated. We have sent you your policy document on the registered email.",
        "otp_verification_failed": "OTP verification is unsuccessful. Calling CRM API to update email ID and sending PDF.",
        "no_email_no_pdf": "Cannot send policy PDF without an email address.",
        "end_flow": "Thank you for contacting SBI General Insurance. Have a nice day!",
        "repeat_prompt": "I didn’t catch that. Could you repeat your {field}?",
        "retry_prompt": "Let’s try again. Please provide your {field}.",
        "invalid_input": "Sorry, I didn't understand that. Please try again.",
        "health_policy_redirect": "This is a health policy. Please use the health claim process.",
        "am_pm_clarify": "Did you mean AM or PM?",
        "email_id_prompt": "Please provide your email id.",
        "thank_you": "Thank you for using the service. Goodbye!",
        "am_pm_invalid": "Please reply with 'AM' or 'PM'.",
        "invalid_mobile": "Please enter a valid 10-digit mobile number.",
        "pdf_sent": "Policy PDF sent to your email."
    },
    "hindi": {
        "welcome": "🤖 नमस्ते, SBI जनरल इंश्योरेंस में आपका स्वागत है।",
        "choose_language": "आप कौन सी भाषा में आगे बढ़ना चाहेंगे? हिंदी, अंग्रेजी, मराठी, या गुजराती?",
        "continue_language": "आप हिंदी में जारी रख सकते हैं।",
        "how_help": "मैं आपकी आज कैसे सहायता कर सकता हूँ?",
        "claim_prompt": "मैं दावा शुरू करने या पॉलिसी पीडीएफ प्राप्त करने में सहायता कर सकता हूँ। कृपया कुछ ऐसा कहें जैसे 'मैं दावा शुरू करना चाहता हूँ' या 'मैं अपनी पॉलिसी पीडीएफ डाउनलोड करना चाहता हूँ।'",
        "mobile_prompt": "कृपया अपना मोबाइल नंबर प्रदान करें।",
        "mobile_registered": "धन्यवाद। यह नंबर हमारे पास पंजीकृत है।",
        "mobile_unregistered": "यह नंबर हमारे पास पंजीकृत नहीं प्रतीत होता।",
        "policy_list": "आपके पास निम्नलिखित पॉलिसियाँ हैं:\n- पॉलिसी 12345678\n- पॉलिसी 87654321",
        "policy_prompt": "आप किस पॉलिसी के साथ आगे बढ़ना चाहेंगे?",
        "policy_number_prompt": "कृपया अपनी पॉलिसी नंबर प्रदान करें।",
        "fetch_policy": "पॉलिसी विवरण प्राप्त कर रहा हूँ, कृपया प्रतीक्षा करें...",
        "otp_registered": "आपके पंजीकृत मोबाइल पर एक ओ.टी.पी भेजा गया है। कृपया छह अंकों का ओ.टी.पी प्रदान करें।",
        "otp_unregistered": "आपके मोबाइल नंबर पर एक ओ.टी.पी भेजा गया है। कृपया छह अंकों का ओ.टी.पी प्रदान करें।",
        "date_prompt": "कृपया मुझे दुर्घटना की तारीख बताएं।",
        "time_prompt": "कृपया मुझे दुर्घटना का समय बताएं।",
        "am_pm_prompt": "कृपया AM या PM निर्दिष्ट करें।",
        "city_prompt": "कृपया मुझे बताएं कि दुर्घटना किस शहर में हुई थी।",
        "state_prompt": "कृपया मुझे बताएं कि दुर्घटना किस राज्य में हुई थी।",
        "driver_prompt": "धन्यवाद। गाड़ी कौन चला रहा था?",
        "email_prompt": "क्या आपके पास साझा करने के लिए ईमेल ID है? (हाँ/नहीं)",
        "ask_email_actual": "कृपया अपना ईमेल आईडी बताएं।",
        "email_confirm": "कृपया पुष्टि करें, क्या यह आपका ईमेल है: {email}? (हाँ/नहीं)",
        "claim_success": "✅ आपका दावा सफलतापूर्वक शुरू हो गया है।",
        "final_data": "📄 अंतिम संरचित डेटा:",
        "policy_pdf_flow": "आइए आपकी पॉलिसी पीडीएफ़ डाउनलोड करने में मदद करें।",
        "policy_pdf_sent": "हमने आपकी पॉलिसी PDF आपके पंजीकृत ईमेल पर भेज दी है। क्या मैं आपकी और सहायता कर सकता हूँ?",
        "send_pdf_email_prompt": "क्या आप अपनी पॉलिसी PDF अपने पंजीकृत ईमेल पर प्राप्त करना चाहेंगे? (हाँ/नहीं)",
        "otp_email": "हमने आपके ईमेल पर OTP भेजा है। कृपया OTP दर्ज करें।",
        "otp_verification_success": "आपका OTP सफलतापूर्वक सत्यापित हो गया है और पंजीकृत ईमेल सफलतापूर्वक अपडेट हो गया है। हमने आपकी पॉलिसी PDF आपके पंजीकृत ईमेल पर भेज दी है।",
        "otp_verification_failed": "OTP सत्यापन असफल रहा। CRM API को कॉल कर ईमेल ID अपडेट कर रहे हैं और PDF भेज रहे हैं।",
        "no_email_no_pdf": "ईमेल के बिना पॉलिसी PDF नहीं भेजी जा सकती।",
        "end_flow": "SBI जनरल इंश्योरेंस से संपर्क करने के लिए धन्यवाद। शुभ दिन!",
        "repeat_prompt": "मुझे वह समझ नहीं आया। कृपया अपनी {field} दोहराएं।",
        "retry_prompt": "चलो फिर से कोशिश करें। कृपया अपना {field} प्रदान करें।",
        "invalid_input": "माफ़ कीजिए, मैं समझ नहीं पाया। कृपया फिर से प्रयास करें।",
        "health_policy_redirect": "यह एक स्वास्थ्य पॉलिसी है। कृपया स्वास्थ्य दावा प्रक्रिया का उपयोग करें।",
        "am_pm_clarify": "क्या आप AM या PM कहना चाहते हैं?",
        "email_id_prompt": "कृपया अपनी ईमेल आईडी बताएं।",
        "thank_you": "सेवा का उपयोग करने के लिए धन्यवाद। अलविदा!",
        "am_pm_invalid": "'AM' या 'PM' के साथ उत्तर दें।",
        "invalid_mobile": "कृपया 10 अंकों का वैध मोबाइल नंबर दर्ज करें।",
        "pdf_sent": "पॉलिसी पीडीएफ आपके ईमेल पर भेजी गई।"
    },
    "marathi": {
        "welcome": "🤖 नमस्कार, SBI जनरल इन्शुरन्समध्ये आपले स्वागत आहे।",
        "choose_language": "आपण कोणत्या भाषेत पुढे जाऊ इच्छिता? हिंदी, इंग्रजी, मराठी, किंवा गुजराती?",
        "continue_language": "आपण मराठीतून सुरू ठेवू शकता.",
        "how_help": "मी आज आपली कशी मदत करू शकतो?",
        "claim_prompt": "मी दावा सुरू करण्यात किंवा पॉलिसी पीडीएफ मिळवण्यात मदत करू शकतो। कृपया असे काही सांगा 'मला दावा सुरू करायचा आहे' किंवा 'मला माझी पॉलिसी पीडीएफ डाउनलोड करायची आहे.'",
        "mobile_prompt": "कृपया आपला मोबाइल नंबर द्या.",
        "mobile_registered": "धन्यवाद. हा नंबर आमच्याकडे नोंदणीकृत आहे.",
        "mobile_unregistered": "हा नंबर आमच्याकडे नोंदणीकृत नाही असे दिसते.",
        "policy_list": "आपल्याकडे खालील पॉलिसी आहेत:\n- पॉलिसी 12345678\n- पॉलिसी 87654321",
        "policy_prompt": "आपण कोणत्या पॉलिसीसाठी पुढे जाऊ इच्छिता?",
        "policy_number_prompt": "कृपया आपला पॉलिसी नंबर सांगा.",
        "fetch_policy": "पॉलिसी तपशील आणत आहे, कृपया प्रतीक्षा करा...",
        "otp_registered": "आम्ही आपल्या नोंदणीकृत मोबाइलवर OTP पाठवला आहे। कृपया 6 अंकीय OTP द्या.",
        "otp_unregistered": "आम्ही आपल्या मोबाइल नंबरवर OTP पाठवला आहे। कृपया 6 अंकीय OTP सांगा.",
        "date_prompt": "कृपया मला अपघाताची तारीख सांगा.",
        "time_prompt": "कृपया मला अपघाताचा वेळ सांगा.",
        "am_pm_prompt": "कृपया AM किंवा PM नमूद करा.",
        "city_prompt": "कृपया मला सांगा की अपघात कोणत्या शहरात झाला?",
        "state_prompt": "कृपया मला सांगा की अपघात कोणत्या राज्यात झाला?",
        "driver_prompt": "धन्यवाद. गाडी कोण चालवत होता?",
        "email_prompt": "आपल्याकडे शेअर करण्यासाठी ईमेल ID आहे का? (होय/नाही)",
        "ask_email_actual": "कृपया आपला ईमेल आयडी सांगा.",
        "email_confirm": "कृपया पुष्टी करा, हा तुमचा ईमेल आहे का: {email}? (होय/नाही)",
        "claim_success": "✅ आपला दावा यशस्वीपणे सुरू झाला आहे.",
        "final_data": "📄 अंतिम संरचित डेटा:",
        "policy_pdf_flow": "चला, तुमची पॉलिसी PDF डाउनलोड करूया.",
        "policy_pdf_sent": "आम्ही तुमची पॉलिसी PDF तुमच्या नोंदणीकृत ईमेलवर पाठवली आहे. आणखी काही मदत हवी आहे का?",
        "send_pdf_email_prompt": "तुम्हाला तुमची पॉलिसी PDF नोंदणीकृत ईमेलवर हवी आहे का? (होय/नाही)",
        "otp_email": "आम्ही तुमच्या ईमेलवर OTP पाठवला आहे। कृपया OTP प्रविष्ट करा。",
        "otp_verification_success": "तुमचा OTP यशस्वीपणे पडताळला गेला आहे आणि नोंदणीकृत ईमेल यशस्वीपणे अपडेट केला आहे। आम्ही तुमची पॉलिसी PDF तुमच्या नोंदणीकृत ईमेलवर पाठवली आहे।",
        "otp_verification_failed": "OTP पडताळणी अयशस्वी. CRM API कॉल करून ईमेल ID अपडेट करत आहोत आणि PDF पाठवत आहोत।",
        "no_email_no_pdf": "ईमेल पत्ता न दिल्यास पॉलिसी PDF पाठवता येणार नाही।",
        "end_flow": "SBI जनरल इन्शुरन्समध्ये संपर्क केल्याबद्दल धन्यवाद। शुभेच्छा!",
        "repeat_prompt": "मला ते समजलं नाही। कृपया आपलं {field} पुन्हा सांगा।",
        "retry_prompt": "पुन्हा प्रयत्न करूया। कृपया आपलं {field} द्या।",
        "invalid_input": "माफ करा, मला ते समजले नाही। कृपया पुन्हा प्रयत्न करा।",
        "health_policy_redirect": "ही एक आरोग्य पॉलिसी आहे। कृपया आरोग्य दावा प्रक्रियेचा वापर करा।",
        "am_pm_clarify": "तुम्हाला AM की PM म्हणायचे आहे का?",
        "email_id_prompt": "कृपया आपला ईमेल आयडी सांगा।",
        "thank_you": "सेवेचा वापर केल्याबद्दल धन्यवाद। गुडबाय!",
        "am_pm_invalid": "'AM' किंवा 'PM' असे उत्तर द्या।",
        "invalid_mobile": "कृपया 10 अंकों का वैध मोबाइल नंबर दर्ज करें।",
        "pdf_sent": "पॉलिसी पीडीएफ तुमच्या ईमेलवर पाठवली आहे."
    },
    "gujarati": {
        "welcome": "🤖 નમસ્તે, SBI જનરલ ઇન્સ્યોરન્સમાં તમારું સ્વાગત છે।",
        "choose_language": "તમે કઈ ભાષામાં આગળ વધવા માંગો છો? હિન્દી, અંગ્રેજી, મરાઠી, કે ગુજરાતી?",
        "continue_language": "તમે ગુજરાતીમાં આગળ વધી શકો છો।",
        "how_help": "હું આજે તમારી કેવી રીતે મદદ કરી શકું?",
        "claim_prompt": "હું દાવો શરૂ કરવામાં કે પોલિસી પીડીએફ મેળવવામાં મદદ કરી શકું છું। કૃપા કરીને 'હું દાવો શરૂ કરવા માંગું છું' કે 'હું મારી પોલિસી પીડીએફ ડાઉનલોડ કરવા માંગું છું' જેવું કંઈક કહો.",
        "mobile_prompt": "કૃપા કરીને તમારો મોબાઇલ નંબર આપો।",
        "mobile_registered": "આભાર. આ નંબર અમારી પાસે નોંધાયેલો છે।",
        "mobile_unregistered": "આ નંબર અમારી પાસે નોંધાયેલો નથી લાગતો।",
        "policy_list": "તમારી પાસે નીચેની પોલિસી છે:\n- પોલિસી 12345678\n- પોલિસી 87654321",
        "policy_prompt": "તમે કઈ પોલિસી સાથે આગળ વધવા માંગો છો?",
        "policy_number_prompt": "કૃપા કરીને તમારો પોલિસી નંબર આપો।",
        "fetch_policy": "પોલિસી વિગતો મેળવી રહ્યો છું, કૃપા કરીને રાહ જુઓ...",
        "otp_registered": "તમારા નોંધાયેલા મોબાઇલ પર OTP મોકલવામાં આવ્યો છે। કૃપા કરીને 6 અંકનો OTP આપો।",
        "otp_unregistered": "તમારા મોબાઇલ નંબર પર OTP મોકલવામાં આવ્યો છે। કૃપા કરીને 6 અંકનો OTP આપો।",
        "date_prompt": "કૃપા કરીને મને અકસ્માતની તારીખ જણાવો।",
        "time_prompt": "કૃપા કરીને મને અકસ્માતનો સમય જણાવો।",
        "am_pm_prompt": "કૃપા કરીને AM કે PM જણાવો।",
        "city_prompt": "કૃપા કરીને મને જણાવો કે અકસ્માત કયા શહેરમાં થયો હતો।",
        "state_prompt": "કૃપા કરીને મને જણાવો કે અકસ્માત કયા રાજ્યમાં થયો હતો।",
        "driver_prompt": "આભાર. કાર કોણ ચલાવી રહ્યું હતું?",
        "email_prompt": "શું તમારી પાસે શેર કરવા માટે ઇમેઇલ આઈડી છે? (હા/ના)",
        "ask_email_actual": "કૃપા કરીને તમારું ઇમેઇલ આઈડી આપો।",
        "email_confirm": "કૃપા કરીને પુષ્ટિ કરો, શું આ તમારું ઇમેઇલ છે: {email}? (હા/ના)",
        "claim_success": "✅ તમારો દાવો સફળતાપૂર્વક શરૂ થયો છે।",
        "final_data": "📄 અંતિમ સંરચિત ડેટા:",
        "policy_pdf_flow": "ચાલો, તમારી પોલિસી PDF ડાઉનલોડ કરીએ।",
        "policy_pdf_sent": "અમે તમારી પોલિસી PDF તમારા નોંધાયેલા ઇમેઇલ પર મોકલી દીધી છે। શું હું તમારી વધુ મદદ કરી શકું?",
        "send_pdf_email_prompt": "શું તમે તમારી પોલિસી PDF તમારા નોંધાયેલા ઇમેઇલ પર મેળવવા માંગો છો? (હા/ના)",
        "otp_email": "અમે તમારા ઇમેઇલ પર OTP મોકલ્યો છે। કૃપા કરીને OTP દાખલ કરો।",
        "otp_verification_success": "તમારો OTP સફળતાપૂર્વક ચકાસાયો છે અને નોંધાયેલું ઇમેઇલ સફળતાપૂર્વક અપડેટ થયું છે। અમે તમારી પોલિસી PDF તમારા નોંધાયેલા ઇમેઇલ પર મોકલી દીધી છે।",
        "otp_verification_failed": "OTP ચકાસણી અસફળ રહી. CRM API ને કૉલ કરીને ઇમેઇલ આઈડી અપડેટ કરી રહ્યા છીએ અને PDF મોકલી રહ્યા છીએ।",
        "no_email_no_pdf": "ઇમેઇલ આઈડી વિના પોલિસી PDF મોકલી શકાતી નથી।",
        "end_flow": "SBI જનરલ ઇન્સ્યોરન્સનો સંપર્ક કરવા બદલ આભાર. શુભ દિવસ!",
        "repeat_prompt": "મને તે સમજાયું નહીં. કૃપા કરીને તમારું {field} ફરીથી કહો。",
        "retry_prompt": "ફરીથી પ્રયાસ કરીએ. કૃપા કરીને તમારું {field} આપો।",
        "invalid_input": "માફ કરશો, મને તે સમજાયું નહીં. કૃપા કરીને ફરીથી પ્રયાસ કરો।",
        "health_policy_redirect": "આ એક આરોગ્ય પોલિસી છે। કૃપા કરીને આરોગ્ય દાવો પ્રક્રિયાનો ઉપયોગ કરો।",
        "am_pm_clarify": "શું તમે AM કે PM કહેવા માંગો છો?",
        "email_id_prompt": "કૃપા કરીને તમારું ઇમેઇલ આઈડી આપો।",
        "thank_you": "સેવાનો ઉપયોગ કરવા બદલ આભાર. ગુડબાય!",
        "am_pm_invalid": "'AM' અથવા 'PM' સાથે જવાબ આપો।",
        "invalid_mobile": "કૃપા કરીને 10 અંકનો માન્ય મોબાઇલ નંબર દાખલ કરો।",
        "pdf_sent": "પોલિસી પીડીએફ તમારા ઇમેઇલ પર મોકલવામાં આવી છે."
    }
}

# Define PROMPTS dictionary to map fields to their prompt strings
PROMPTS = {
    "policy_number": POLICY_NUMBER_PROMPT,
    "otp": OTP_PROMPT,
    "mobile_number": MOBILE_NUMBER_PROMPT,
    "date_of_accident": DATE_OF_ACCIDENT_PROMPT,
    "time_of_accident": TIME_OF_ACCIDENT_PROMPT,
    "am_pm": AM_PM_PROMPT,
    "state_of_accident": STATE_OF_ACCIDENT_PROMPT,
    "city_of_accident": CITY_OF_ACCIDENT_PROMPT,
    "who_driver": WHO_DRIVER_PROMPT,
    "email_id": EMAIL_ID_PROMPT
}