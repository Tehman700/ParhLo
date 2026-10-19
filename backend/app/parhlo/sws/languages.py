"""Language codes for SWS: GDELT gives ISO 639-2/3 ("rus"), we store ISO 639-1 ("ru") and show names ("Russian")."""

# 3-letter → 2-letter, for the languages GDELT translates most (and a few more). Unknown codes are kept as is.
LANG3 = {
    "eng": "en", "rus": "ru", "zho": "zh", "tur": "tr", "deu": "de", "spa": "es", "ita": "it", "ara": "ar",
    "vie": "vi", "ell": "el", "ron": "ro", "fra": "fr", "sqi": "sq", "fin": "fi", "kor": "ko", "bul": "bg",
    "por": "pt", "jpn": "ja", "nld": "nl", "pol": "pl", "ukr": "uk", "heb": "he", "ind": "id", "tha": "th",
    "hin": "hi", "ben": "bn", "urd": "ur", "fas": "fa", "swa": "sw", "ces": "cs", "hun": "hu", "swe": "sv",
    "dan": "da", "nor": "no", "hrv": "hr", "srp": "sr", "slk": "sk", "slv": "sl", "lit": "lt", "lav": "lv",
    "est": "et", "cat": "ca", "msa": "ms", "tam": "ta", "tel": "te", "mar": "mr", "guj": "gu", "kan": "kn",
    "mal": "ml", "pan": "pa", "aze": "az", "kaz": "kk", "uzb": "uz", "mkd": "mk", "bos": "bs", "hye": "hy",
    "kat": "ka", "afr": "af", "amh": "am", "som": "so", "hau": "ha", "yor": "yo", "tgl": "tl", "khm": "km",
    "mya": "my", "nep": "ne", "sin": "si", "pus": "ps", "kur": "ku", "glg": "gl", "eus": "eu", "isl": "is",
}

NAMES = {
    "en": "English", "ru": "Russian", "zh": "Chinese", "tr": "Turkish", "de": "German", "es": "Spanish",
    "it": "Italian", "ar": "Arabic", "vi": "Vietnamese", "el": "Greek", "ro": "Romanian", "fr": "French",
    "sq": "Albanian", "fi": "Finnish", "ko": "Korean", "bg": "Bulgarian", "pt": "Portuguese", "ja": "Japanese",
    "nl": "Dutch", "pl": "Polish", "uk": "Ukrainian", "he": "Hebrew", "id": "Indonesian", "th": "Thai",
    "hi": "Hindi", "bn": "Bengali", "ur": "Urdu", "fa": "Persian", "sw": "Swahili", "cs": "Czech",
    "hu": "Hungarian", "sv": "Swedish", "da": "Danish", "no": "Norwegian", "hr": "Croatian", "sr": "Serbian",
    "sk": "Slovak", "sl": "Slovenian", "lt": "Lithuanian", "lv": "Latvian", "et": "Estonian", "ca": "Catalan",
    "ms": "Malay", "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "az": "Azerbaijani", "kk": "Kazakh", "uz": "Uzbek", "mk": "Macedonian",
    "bs": "Bosnian", "hy": "Armenian", "ka": "Georgian", "af": "Afrikaans", "am": "Amharic", "so": "Somali",
    "ha": "Hausa", "yo": "Yoruba", "tl": "Tagalog", "km": "Khmer", "my": "Burmese", "ne": "Nepali",
    "si": "Sinhala", "ps": "Pashto", "ku": "Kurdish", "gl": "Galician", "eu": "Basque", "is": "Icelandic",
}


def to2(code3: str | None) -> str | None:
    return LANG3.get(code3, code3) if code3 else None


def name(code2: str | None) -> str | None:
    return NAMES.get(code2) if code2 else None
