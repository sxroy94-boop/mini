"""mini - JARVIS style Android voice assistant (Kivy + pyjnius). Single file."""
import collections
import datetime
import json
import math
import os
import random
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Point
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

try:
    import certifi
except Exception:
    certifi = None

ANDROID = platform == "android"
REQ_SPEECH = 4242
MODEL = "gemini-3.1-flash-lite"  # change inside the app: type "use model <name>"
GOLD = (1, 0.76, 0.2, 1)
MEMORY_DAYS = 35
IDLE_SLEEP_SECONDS = 15 * 60
PROACTIVE_SECONDS = 5 * 60
WAKE = re.compile(r"\b(?:mini|minnie|meeni|mini's)\b")

if ANDROID:
    from android import activity as android_activity
    from android.permissions import Permission, check_permission, request_permissions
    from android.runnable import run_on_ui_thread
    from jnius import PythonJavaClass, autoclass, cast, java_method

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    Locale = autoclass("java.util.Locale")
    Context = autoclass("android.content.Context")
    Settings = autoclass("android.provider.Settings")
    AudioManager = autoclass("android.media.AudioManager")
    IntentFilter = autoclass("android.content.IntentFilter")
    SmsManager = autoclass("android.telephony.SmsManager")

    class TTSInit(PythonJavaClass):
        __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
        __javacontext__ = "app"

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(I)V")
        def onInit(self, status):
            self.callback(status)

    class RecListener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/RecognitionListener"]
        __javacontext__ = "app"

        def __init__(self, on_text, on_error):
            super().__init__()
            self.on_text = on_text
            self.on_error = on_error

        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params):
            pass

        @java_method("()V")
        def onBeginningOfSpeech(self):
            pass

        @java_method("(F)V")
        def onRmsChanged(self, rms):
            pass

        @java_method("([B)V")
        def onBufferReceived(self, buf):
            pass

        @java_method("()V")
        def onEndOfSpeech(self):
            pass

        @java_method("(I)V")
        def onError(self, code):
            self.on_error(code)

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            text = ""
            lst = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            if lst is not None and lst.size() > 0:
                first = lst.get(0)
                text = first if isinstance(first, str) else first.toString()
            self.on_text(text)

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partial):
            pass

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, event, params):
            pass

else:

    def run_on_ui_thread(f):
        return f


# ================================================================ replies
Reply = collections.namedtuple("Reply", "spoken shown")
DEVA = re.compile(r"[\u0900-\u097F]")
NUM = re.compile(r"\d[\d:.,]*(?:\s?[AaPp]\.?[Mm]\.?)?")


def R(spoken, shown=None):
    return Reply(spoken, spoken if shown is None else shown)


def has_deva(text):
    return bool(DEVA.search(text))


def segments(text, base):
    """Split text so numbers are always spoken with the English voice."""
    out, pos = [], 0
    for m in NUM.finditer(text):
        if m.start() > pos:
            out.append((base, text[pos:m.start()]))
        out.append(("en", m.group()))
        pos = m.end()
    if pos < len(text):
        out.append((base, text[pos:]))
    return [(lang, s) for lang, s in out if s.strip()]


# {n} is replaced by the user's nickname. Each value is (spoken, shown).
# Hindi is spoken in Devanagari but shown in Roman letters (no font needed).
RESP = {
    "hello": {
        "normal": ("नमस्ते {n}! कैसे हो?", "Namaste {n}! Kaise ho?"),
        "personal": ("नमस्ते {n}! आप कैसे हो?", "Namaste {n}! Aap kaise ho?"),
    },
    "kaise": {
        "normal": ("मैं ठीक हूँ! आप कैसे हो?", "Main theek hoon! Aap kaise ho?"),
        "personal": (
            "मैं ठीक हूँ, आपसे बात करके अच्छा लगा। आप कैसे हो {n}?",
            "Main theek hoon, aapse baat karke accha laga. Aap kaise ho {n}?",
        ),
    },
    "howare": {"normal": ("मैं ठीक हूँ", "Main theek hoon")},
    "thanks": {"normal": ("आपका स्वागत है {n}", "Aapka swagat hai {n}")},
    "name": {"normal": ("मेरा नाम मिनी है", "Mera naam Mini hai")},
    "gmorning": {
        "normal": ("गुड मॉर्निंग {n}! आप कैसे हो?", "Good morning {n}! Aap kaise ho?"),
    },
    "love": {
        "normal": ("धन्यवाद {n}, मैं यहाँ मदद के लिए हूँ।", "Dhanyavad {n}, main yahan madad ke liye hoon."),
    },
    "sorry": {"normal": ("कोई बात नहीं {n}!", "Koi baat nahin {n}!")},
    "yes": {"normal": ("ओके {n}!", "Okay {n}!")},
    "no": {"normal": ("ठीक है {n}.", "Theek hai {n}.")},
    "ok": {"normal": ("ठीक है {n}!", "Theek hai {n}!")},
}

PATTERNS = [
    ("hello", r"hello|hi|hey|hello there|hi there|namaste|namaskar|नमस्ते"),
    ("kaise", r"(?:aap )?kaise ho|(?:aap )?kaisi ho|kese ho|kaisa hai|आप कैसे हो|कैसे हो"),
    ("howare", r"how are you|how r u|how are you doing"),
    ("thanks", r"thank you|thanks|thank u|shukriya|dhanyavad|धन्यवाद|शुक्रिया"),
    ("name", r"what(?:'s| is) your name|tumhara naam kya hai|aapka naam kya hai|तुम्हारा नाम क्या है|आपका नाम क्या है"),
    ("gmorning", r"good morning|suprabhat|सुप्रभात"),
    ("sorry", r"sorry|maaf karo|maaf kijiye|सॉरी"),
    ("yes", r"yes|haan|han|ha|हाँ|हां"),
    ("no", r"no|nahi|nahin|nope|नहीं"),
    ("ok", r"ok|okay|thik hai|theek hai|ठीक है"),
]
LOVE = r"i love you|love you|i love u|आई लव यू"
ASK_AFTER = {"hello", "kaise", "howare", "gmorning", "thanks", "yes", "no", "ok", "sorry"}

PERS_QUESTIONS = [
    R("आप कैसे हो {n}?", "Aap kaise ho {n}?"),
    R("क्या कर रहे हो?", "Kya kar rahe ho?"),
    R("आज का दिन कैसा रहा?", "Aaj ka din kaisa raha?"),
]
PROACTIVE = {
    "normal": [
        R("क्या आपको कुछ चाहिए {n}?", "Kya aapko kuch chahiye {n}?"),
        R("मैं यहीं हूँ, बताइए।", "Main yahin hoon, bataiye."),
        R("I am here if you need me, {n}."),
    ],
    "personal": PERS_QUESTIONS + [R("Boss, aaj kaisa din tha?", "Boss, aaj kaisa din tha?")],
}

APP_ALIASES = {
    "chrome": ["com.android.chrome"],
    "youtube": ["com.google.android.youtube"],
    "whatsapp": ["com.whatsapp"],
    "facebook": ["com.facebook.katana"],
    "instagram": ["com.instagram.android"],
    "telegram": ["org.telegram.messenger"],
    "chatgpt": ["com.openai.chatgpt"],
    "google": ["com.google.android.googlequicksearchbox"],
    "gmail": ["com.google.android.gm"],
    "maps": ["com.google.android.apps.maps"],
    "play store": ["com.android.vending"],
    "spotify": ["com.spotify.music"],
    "netflix": ["com.netflix.mediaclient"],
    "vlc": ["org.videolan.vlc"],
    "phonepe": ["com.phonepe.app"],
    "paytm": ["net.one97.paytm"],
    "gpay": ["com.google.android.apps.nbu.paisa.user"],
    "google pay": ["com.google.android.apps.nbu.paisa.user"],
    "zomato": ["com.application.zomato"],
    "swiggy": ["in.swiggy.android"],
    "flipkart": ["com.flipkart.android"],
    "amazon": ["in.amazon.mShop.android.shopping", "com.amazon.mShop.android.shopping"],
}


# ================================================================ storage + brain (no Android code)
class Store:
    def __init__(self, folder):
        self.folder = folder

    def path(self, name):
        return os.path.join(self.folder, name)

    def load(self, name, default):
        try:
            with open(self.path(name), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def save(self, name, data):
        with open(self.path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def read_text(self, name, default=""):
        try:
            with open(self.path(name), encoding="utf-8") as f:
                return f.read().strip() or default
        except Exception:
            return default

    def write_text(self, name, value):
        with open(self.path(name), "w", encoding="utf-8") as f:
            f.write(value)


class Memory:
    """mini_mem.json - every item has a timestamp, deleted after 35 days."""

    FILE = "mini_mem.json"

    def __init__(self, store, clock=time.time):
        self.store = store
        self.clock = clock
        self.cleanup()

    def cleanup(self):
        data = self.store.load(self.FILE, {})
        limit = self.clock() - MEMORY_DAYS * 86400
        kept = {k: v for k, v in data.items() if v.get("t", 0) >= limit}
        if len(kept) != len(data):
            self.store.save(self.FILE, kept)
        return kept

    def remember(self, key, value):
        data = self.cleanup()
        data[key] = {"v": value, "t": self.clock()}
        self.store.save(self.FILE, data)

    def recall(self, key):
        item = self.cleanup().get(key)
        return item["v"] if item else None

    def clear(self):
        self.store.save(self.FILE, {})


class Vault:
    """mini_pwd.json - kept forever, never auto-deleted."""

    FILE = "mini_pwd.json"

    def __init__(self, store):
        self.store = store

    def set(self, password):
        self.store.save(self.FILE, {"password": password})

    def get(self):
        return self.store.load(self.FILE, {}).get("password")


class Brain:
    """Turns what the user said into an action. Pure Python, easy to test."""

    def __init__(self, store, clock=time.time, now=datetime.datetime.now, rnd=None):
        self.mem = Memory(store, clock)
        self.vault = Vault(store)
        self.now = now
        self.rnd = rnd or random.Random()
        self.mood = "normal"

    @property
    def nick(self):
        return self.mem.recall("nickname") or "boss"

    def fmt(self, r):
        n = self.nick
        return Reply(r.spoken.replace("{n}", n), r.shown.replace("{n}", n))

    def clean(self, raw):
        s = raw.lower()
        s = re.sub(r"(?:\b(?:hey|ok|okay)\s+)?\b(?:mini|minnie)\b", " ", s)
        return re.sub(r"\s+", " ", s).strip(" ,.!?।")

    def greeting(self):
        h = self.now().hour
        if 6 <= h < 12:
            r = R("Good morning {n}!")
        elif 12 <= h < 17:
            r = R("Good afternoon! आपका दिन कैसा गया है?", "Good afternoon! Aapka din kaisa gaya hai?")
        elif 17 <= h < 22:
            r = R("Good evening! आज का दिन कैसा था?", "Good evening! Aaj ka din kaisa tha?")
        elif h == 22:
            r = R("दिन हो गया है। आप डिनर कर लीजिए।", "Din ho gaya hai. Aap dinner kar lijiye.")
        else:
            r = R("Good night! Sweet dreams.")
        return self.fmt(r)

    def proactive(self):
        return self.fmt(self.rnd.choice(PROACTIVE.get(self.mood, PROACTIVE["normal"])))

    def system_prompt(self):
        base = (
            "You are mini, a JARVIS-like voice assistant on an Android phone. "
            "Always address the user only as %s, never any other name or pet name. "
            "Never use romantic language. Answer in one or two short spoken sentences. "
            "Reply in the language the user used: English or Hindi. "
            "For an English reply output exactly: EN@@<text> "
            "For a Hindi reply output exactly: HI@@<Hindi in Devanagari script>@@<the same sentence in Roman letters> "
            "Write numbers as digits. No markdown, no emojis. Never use Bengali."
        ) % self.nick
        if self.mood == "personal":
            base += " Use a soft, caring, but respectful and non-romantic tone, and sometimes ask how the user is."
        return base

    def parse_ai(self, text):
        t = text.strip()
        if t.startswith("HI@@"):
            parts = t[4:].split("@@")
            spoken = parts[0].strip()
            shown = parts[1].strip() if len(parts) > 1 else spoken
            if has_deva(shown):
                shown = "(Hindi voice reply)"
            return R(spoken, shown)
        if t.startswith("EN@@"):
            t = t[4:].strip()
        return R(t, "(Hindi voice reply)" if has_deva(t) else t)

    def _mood_reply(self, key):
        table = RESP[key]
        sp, sh = table.get(self.mood) or table["normal"]
        r = self.fmt(R(sp, sh))
        if key in ASK_AFTER and self.mood == "personal" and not r.shown.rstrip().endswith("?"):
            if self.rnd.random() < 0.5:
                q = self.fmt(self.rnd.choice(PERS_QUESTIONS))
                r = Reply(r.spoken + " " + q.spoken, r.shown + " " + q.shown)
        return r

    def route(self, raw):
        """Return (kind, payload). Kinds: say, stop, off, vault_save, vault_get,
        online, model, cc, call, open, search, whatsapp, weather, ai, empty."""
        raw = raw.strip()
        if not raw:
            return ("empty", None)
        full = re.sub(r"\s+", " ", raw.lower()).strip(" ,.!?।")
        low = self.clean(raw)

        if re.fullmatch(
            r"(?:(?:hey|ok|okay) )?mini (?:off|band karo|shutdown|switch off)|(?:shut ?down|power off) mini", full
        ):
            return ("off", self.fmt(R("Switching off. Goodbye {n}!", "Switching off. Alvida {n}!")))

        # password vault (checked first so it never reaches the AI)
        m = re.match(r"^(?:save )?my password is (.+)$", raw, re.I) or re.match(
            r"^(?:save )?mera password (?!kya\b)(.+?)(?: hai)?$", raw, re.I
        )
        if m:
            self.vault.set(m.group(1).strip(" ."))
            return ("vault_save", R("Password saved.", "Password saved."))
        if re.fullmatch(
            r"what(?:'s| is) my password|tell me my password|mera password kya hai|मेरा पासवर्ड क्या है", low
        ):
            pw = self.vault.get()
            if not pw:
                return ("vault_get", R("You have not saved a password yet."))
            spelled = " ".join(pw)
            return ("vault_get", R("Your password is " + spelled, "Your password is ******** (spoken only)"))

        if not low:
            return ("say", self.fmt(R("जी {n}?", "Ji {n}?")))

        # stop commands
        if re.fullmatch(r"bye|good ?bye|stop|band|band karo|band kar do|by|bey|बंद|अलविदा|alvida", low):
            return ("stop", self.fmt(R("अलविदा {n}!", "Alvida {n}!")))
        if re.fullmatch(r"good ?night|gud night|shubh ratri|शुभ रात्रि", low):
            if self.mood == "normal":
                return ("stop", self.fmt(R("Good night {n}!")))
            return ("stop", self.fmt(R("Good night {n}! Sweet dreams.")))

        # online / offline
        m = re.fullmatch(r"(?:(?:go|switch|turn|set)(?: to)? )?(online|offline)(?: mode)?", low)
        if m:
            return ("online", m.group(1) == "online")

        # moods (girlfriend mode is not supported - mini stays a respectful assistant)
        if re.fullmatch(r"personal (?:mode|mood) off|normal (?:mode|mood)|normal ho ja(?:o)?", low):
            self.mood = "normal"
            return ("say", R("Normal mode on."))
        if re.fullmatch(r"(?:girlfriend|gf) (?:mode|mood)(?: on| chalu)?", low):
            return ("say", self.fmt(R("I do not have a girlfriend mode, {n}. I can switch to personal mode instead.")))
        if re.fullmatch(r"personal (?:mode|mood)(?: on)?|पर्सनल मोड", low):
            self.mood = "personal"
            return ("say", self.fmt(R("ठीक है, पर्सनल मोड चालू। आप कैसे हो?", "Theek hai, personal mode on. Aap kaise ho?")))

        # settings
        m = re.match(r"^(?:use|set) model\s+(\S+)$", raw.strip(" .!?"), re.I)
        if m:
            return ("model", m.group(1))
        m = re.fullmatch(r"(?:set )?country code \+?(\d{1,3})", low)
        if m:
            return ("cc", m.group(1))

        # memory
        if re.fullmatch(r"what(?:'s| is) my name|mera naam kya hai|who am i|मेरा नाम क्या है", low):
            name = self.mem.recall("name")
            if name:
                return ("say", R("आपका नाम %s है।" % name, "Aapka naam %s hai." % name))
            return ("say", R("I do not know your name yet. Say: my name is, and your name."))
        if re.fullmatch(r"forget everything|forget all|sab kuch bhool jao|sab bhool jao|सब भूल जाओ", low):
            self.mem.clear()
            return ("say", R("Done. I have forgotten everything."))
        m = re.match(r"^call me (.+)$", raw, re.I) or re.match(r"^mujhe (.+) bula(?:o|na)$", raw, re.I)
        if m:
            nick = m.group(1).strip(" .!?")
            self.mem.remember("nickname", nick)
            return ("say", R("Okay, I will call you %s." % nick))
        m = re.match(r"^my name is (.+)$", raw, re.I) or re.match(
            r"^mera naam (?!kya\b)(.+?)(?: hai)?$", raw, re.I
        )
        if m:
            name = m.group(1).strip(" .!?")
            self.mem.remember("name", name)
            return ("say", R("Nice to meet you, %s." % name))

        # fixed replies
        if re.search(LOVE, low):
            return ("say", self._mood_reply("love"))
        if re.fullmatch(r"good (?:afternoon|evening)", low):
            return ("say", self.greeting())
        for key, rx in PATTERNS:
            if re.fullmatch(rx, low):
                return ("say", self._mood_reply(key))

        # phone hardware controls (checked before the generic open/call handlers below,
        # so "open wifi settings" does not get treated as "open an app called wifi settings")
        if re.fullmatch(
            r"(?:turn on|switch on) (?:the )?(?:torch|flash|flashlight)|(?:torch|flash|flashlight) on|"
            r"torch jalao|flash jalao|light jalao",
            low,
        ):
            return ("torch", True)
        if re.fullmatch(
            r"(?:turn off|switch off) (?:the )?(?:torch|flash|flashlight)|(?:torch|flash|flashlight) off|"
            r"torch bandh karo|flash bandh karo|light bandh karo",
            low,
        ):
            return ("torch", False)
        if re.fullmatch(r"volume up|increase volume|awaaz badhao|volume badhao|volume badha do", low):
            return ("volume", "up")
        if re.fullmatch(r"volume down|decrease volume|awaaz kam karo|volume kam karo", low):
            return ("volume", "down")
        if re.fullmatch(r"(?:full|max(?:imum)?) volume|volume max|volume full karo", low):
            return ("volume", "max")
        if re.fullmatch(r"mute|mute (?:the )?volume|awaaz band karo|volume band karo|silent", low):
            return ("volume", "mute")
        if re.fullmatch(r"unmute|volume on|awaaz chalu karo", low):
            return ("volume", "unmute")
        if re.fullmatch(r"(?:open )?wifi(?: settings)?|wifi kholo|wifi on karo|wifi off karo", low):
            return ("settings", "wifi")
        if re.fullmatch(
            r"(?:open )?bluetooth(?: settings)?|bluetooth kholo|bluetooth on karo|bluetooth off karo", low
        ):
            return ("settings", "bluetooth")
        if re.fullmatch(r"open settings|phone settings|settings kholo", low):
            return ("settings", "settings")
        if re.search(r"battery (?:percentage|status|level)?|battery kitni hai|kitni battery hai", low):
            return ("battery", None)

        # send sms
        m = re.match(
            r"^(?:send )?(?:message|sms|text)\s+(.+?)\s+(?:saying|that says|ki|likh(?:o|ke))\s+(.+)$",
            raw,
            re.I,
        ) or re.match(r"^(.+?)\s+ko\s+(?:message|sms)\s+(?:bhejo|karo)\s+(.+)$", raw, re.I)
        if m:
            return ("sms", (m.group(1).strip(), m.group(2).strip()))

        # phone commands
        m = re.match(r"^whatsapp\s+(?:me\s+|mein\s+)?(.+)$", low)
        if m:
            name = re.sub(
                r"\s+(?:ko\s+)?(?:call|kall|message|msg|chat|text)(?:\s+\w+)?$", "", m.group(1)
            ).strip()
            return ("whatsapp", name)
        m = re.match(r"^(?:call|phone|dial)\s+(.+)$", low) or re.match(
            r"^(.+?)\s+ko\s+(?:call|phone)(?:\s+(?:karo|kro|kar do))?$", low
        )
        if m:
            return ("call", m.group(1).strip())
        m = re.match(r"^(?:open|launch|start)\s+(.+)$", low) or re.match(
            r"^(.+?)\s+(?:kholo|khol do|chalu karo)$", low
        )
        if m:
            return ("open", re.sub(r"\s+app$", "", m.group(1).strip()))
        m = re.match(r"^(?:search|google)(?: for)?\s+(.+)$", low)
        if m:
            return ("search", m.group(1).strip())

        # time, date, weather
        if re.search(
            r"what(?:'s| is)? the time|what time is it|current time|tell me the time|^time$", low
        ):
            return ("say", self.time_reply("en"))
        if re.search(r"time kya hai|samay kya hai|टाइम क्या है|समय क्या है|kitne baje", low):
            return ("say", self.time_reply("hi"))
        if re.search(
            r"what(?:'s| is)? (?:the )?date|today'?s date|what day is it|which day is it", low
        ):
            return ("say", self.date_reply("en"))
        if re.search(r"aaj ki (?:date|tareekh|tarikh)|date kya hai|आज की (?:तारीख|डेट)", low):
            return ("say", self.date_reply("hi"))
        if re.search(r"weather|mausam|मौसम", low):
            lang = "hi" if re.search(r"mausam|kaisa|kya|मौसम|कैसा", low) else "en"
            city = ""
            m = re.search(r"weather (?:in|of|at|for) (.+)$", low)
            if m:
                city = m.group(1).strip()
            return ("weather", (lang, city))

        return ("ai", raw)

    def time_reply(self, lang):
        t = self.now().strftime("%I:%M %p").lstrip("0")
        if lang == "hi":
            return R("अभी समय %s है।" % t, "Abhi samay %s hai." % t)
        return R("The time is %s." % t)

    def date_reply(self, lang):
        d = self.now()
        text = "%d %s %d" % (d.day, d.strftime("%B"), d.year)
        if lang == "hi":
            return R("आज की तारीख %s है।" % text, "Aaj ki tareekh %s hai." % text)
        return R("Today is %s, %s." % (d.strftime("%A"), text))

    def weather_reply(self, lang, temp, unit, cond):
        unit_en = "Celsius" if unit == "C" else "Fahrenheit"
        t = int(temp)
        spoken_t = ("minus %d" % abs(t)) if t < 0 else str(t)
        cond = cond.strip().lower()
        if lang == "hi":
            unit_hi = "सेल्सियस" if unit == "C" else "फ़ारेनहाइट"
            return R(
                "अभी तापमान %s डिग्री %s है और मौसम %s है।" % (spoken_t, unit_hi, cond),
                "Abhi taapmaan %s degree %s hai aur mausam %s hai." % (spoken_t, unit_en, cond),
            )
        return R("It is %s degrees %s and %s." % (spoken_t, unit_en, cond))


# ================================================================ Orb (UI)
STATE_SPEED = {"idle": 10, "listening": 42, "thinking": 115, "speaking": 55, "sleep": 3}
STATE_AMP = {"idle": 0.03, "listening": 0.07, "thinking": 0.045, "speaking": 0.08, "sleep": 0.01}
STATE_GLOW = {"idle": 1.0, "listening": 1.6, "thinking": 1.35, "speaking": 1.9, "sleep": 0.4}


class Orb(Widget):
    """JARVIS style pulsing golden rings. Always turns anticlockwise."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.state = "idle"
        self.tap_cb = None
        self.t = 0.0
        self.ang = 0.0
        self.amp = 0.03

        with self.canvas:
            self.c_g2 = Color(0.9, 0.5, 0.05, 0.10)
            self.glow2 = Ellipse()
            self.c_g1 = Color(1, 0.65, 0.1, 0.18)
            self.glow1 = Ellipse()

            Color(1, 0.72, 0.15, 0.9)
            self.ring_out = Line(width=dp(1.6))
            Color(1, 0.65, 0.1, 0.7)
            self.ring_mid = Line(width=dp(1.3), dash_length=dp(9), dash_offset=dp(6))
            Color(1, 0.55, 0.05, 0.55)
            self.ring_in = Line(width=dp(1.1), dash_length=dp(5), dash_offset=dp(4))

            Color(1, 0.8, 0.3, 0.9)
            self.ticks = Point(pointsize=dp(1.8))

            Color(1, 0.95, 0.7, 1)
            self.core = Ellipse()
        Clock.schedule_interval(self.tick, 1 / 30.0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.tap_cb:
            self.tap_cb()
            return True
        return super().on_touch_down(touch)

    def tick(self, dt):
        st = self.state
        self.t += dt
        self.ang += STATE_SPEED[st] * dt  # positive angle = anticlockwise on screen

        target = STATE_AMP[st]
        if st == "speaking":
            target = 0.05 + 0.09 * abs(math.sin(self.t * 8) * math.sin(self.t * 2.6))
        self.amp += (target - self.amp) * min(1.0, dt * 8)
        breathe = 1.0 if st == "speaking" else math.sin(self.t * 2.2)
        scale = 1 + self.amp * breathe

        cx, cy = self.center_x, self.center_y
        R_ = min(self.width, self.height) * 0.42 * scale

        self.ring_out.circle = (cx, cy, R_)
        self.ring_mid.circle = (cx, cy, R_ * 0.78)
        self.ring_mid.dash_offset = self.ang % 100
        self.ring_in.circle = (cx, cy, R_ * 0.56)
        self.ring_in.dash_offset = (self.ang * 1.7) % 100

        pts = []
        for i in range(12):
            a = math.radians(i * 30 + self.ang)
            r = R_ * 0.90
            pts.extend((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.ticks.points = pts

        g1, g2 = R_ * 1.3, R_ * 1.65
        self.glow1.pos = (cx - g1, cy - g1)
        self.glow1.size = (2 * g1, 2 * g1)
        self.glow2.pos = (cx - g2, cy - g2)
        self.glow2.size = (2 * g2, 2 * g2)
        boost = STATE_GLOW[st]
        self.c_g1.a = min(0.4, 0.16 * boost)
        self.c_g2.a = min(0.28, 0.10 * boost)

        rc = R_ * 0.12 * (1 + 1.6 * self.amp)
        self.core.pos = (cx - rc, cy - rc)
        self.core.size = (2 * rc, 2 * rc)


# ================================================================ helpers
def call_tablet(ip, text, port=5000, timeout=12):
    """Send one line of text to the mini Brain server running on the tablet."""
    url = "http://%s:%d/command" % (ip, port)
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call_gemini(key, model, system, contents):
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 1024},
        }
    ).encode()
    req = urllib.request.Request(
        url, data=body, headers={"content-type": "application/json", "x-goog-api-key": key}
    )
    with urllib.request.urlopen(req, timeout=40, context=ssl_context()) as r:
        out = json.loads(r.read().decode())
    cands = out.get("candidates") or [{}]
    parts = (cands[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def ssl_context():
    if certifi:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def fetch_weather(city):
    url = "https://wttr.in/%s?format=%%t+%%C" % urllib.parse.quote(city)
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=15, context=ssl_context()) as r:
        txt = r.read().decode("utf-8", "ignore").strip()
    m = re.match(r"([+-]?\d+)\s*\S?\s*([CF])\s*(.*)", txt)
    if not m:
        raise ValueError("no weather data")
    return m.group(1).lstrip("+"), m.group(2), m.group(3) or "clear"


def fetch_instant_answer(query):
    """A short spoken answer from DuckDuckGo's instant-answer API, or None if it has nothing."""
    url = "https://api.duckduckgo.com/?q=%s&format=json&no_html=1&skip_disambig=1" % urllib.parse.quote(
        query
    )
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=12, context=ssl_context()) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    text = (data.get("AbstractText") or data.get("Answer") or "").strip()
    if not text:
        topics = data.get("RelatedTopics") or []
        for t in topics:
            if isinstance(t, dict) and t.get("Text"):
                text = t["Text"].strip()
                break
    if not text:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:2])[:400]


def find_number(name):
    act = PythonActivity.mActivity
    phone = autoclass("android.provider.ContactsContract$CommonDataKinds$Phone")
    cur = act.getContentResolver().query(
        phone.CONTENT_URI, ["display_name", "data1"], None, None, None
    )
    found = None
    if cur is not None:
        try:
            while cur.moveToNext():
                if name in (cur.getString(0) or "").lower():
                    found = re.sub(r"[^\d+]", "", cur.getString(1) or "")
                    break
        finally:
            cur.close()
    return found


def find_name(number):
    """Reverse lookup: saved contact name for an incoming phone number, or None."""
    if not number:
        return None
    act = PythonActivity.mActivity
    lookup = autoclass("android.provider.ContactsContract$PhoneLookup")
    uri = Uri.withAppendedPath(lookup.CONTENT_FILTER_URI, Uri.encode(number))
    cur = act.getContentResolver().query(uri, ["display_name"], None, None, None)
    name = None
    if cur is not None:
        try:
            if cur.moveToFirst():
                name = cur.getString(0)
        finally:
            cur.close()
    return name


def styled_button(text, **kw):
    return Button(
        text=text, background_normal="", background_color=(0.22, 0.15, 0.02, 1), color=GOLD, **kw
    )


def styled_input(hint, **kw):
    return TextInput(
        hint_text=hint,
        multiline=False,
        background_color=(0.06, 0.06, 0.09, 1),
        foreground_color=GOLD,
        hint_text_color=(0.55, 0.45, 0.2, 1),
        cursor_color=GOLD,
        **kw
    )


# ================================================================ App
class Mini(App):
    title = "mini"

    def build(self):
        Window.softinput_mode = "below_target"
        Window.clearcolor = (0.01, 0.015, 0.03, 1)
        self.store = Store(self.user_data_dir)
        self.brain = Brain(self.store)
        cfg = self.store.load("mini_set.json", {})
        self.online = bool(cfg.get("online", False))
        self.proactive_on = bool(cfg.get("proactive", False))
        self.cc = cfg.get("cc", "91")
        self.brain.mood = cfg.get("mood", "normal")
        self.model = cfg.get("model", MODEL)
        if self.model.startswith(("gemini-1.5", "gemini-2.0")):
            self.model = MODEL
        self.tablet_on = bool(cfg.get("tablet_on", False))
        self.tablet_ip = cfg.get("tablet_ip", "")

        self.history = []
        self.lines = []
        self.tts = None
        self.tts_ready = False
        self.hi_ok = False
        self.pending = None
        self.sr = None
        self.rec_listener = None
        self.always = False
        self.asleep = False
        self.sr_fail = 0
        self.call_receiver = None
        self.last_call_key = None
        now = time.time()
        self.last_user = now
        self.last_any = now
        self.last_clean = now
        self.conv_until = 0

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.add_widget(
            Label(text="M  I  N  I", color=GOLD, font_size="20sp", size_hint_y=None, height=dp(34))
        )
        self.orb = Orb(size_hint_y=0.45)
        self.orb.tap_cb = self.listen
        root.add_widget(self.orb)

        self.scroll = ScrollView(size_hint_y=0.22)
        self.log = Label(size_hint_y=None, halign="center", valign="top", font_size="15sp", color=GOLD)
        self.log.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        self.log.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.scroll.add_widget(self.log)
        root.add_widget(self.scroll)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.inp = styled_input("Type a command")
        self.inp.bind(on_text_validate=self.on_send)
        row.add_widget(self.inp)
        row.add_widget(styled_button("Send", size_hint_x=None, width=dp(80), on_release=self.on_send))
        root.add_widget(row)

        root.add_widget(
            styled_button("SPEAK", size_hint_y=None, height=dp(60), font_size="22sp", on_release=self.listen)
        )

        row3 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.mode_btn = styled_button("", font_size="13sp", on_release=self.toggle_mode)
        self.listen_btn = styled_button("", font_size="13sp", on_release=self.toggle_listen)
        self.pro_btn = styled_button("", font_size="13sp", on_release=self.toggle_pro)
        self.tablet_btn = styled_button("", font_size="13sp", on_release=self.toggle_tablet)
        for b in (self.mode_btn, self.listen_btn, self.pro_btn, self.tablet_btn):
            row3.add_widget(b)
        root.add_widget(row3)

        keyrow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.key_inp = styled_input("Google Gemini API key", password=True)
        keyrow.add_widget(self.key_inp)
        keyrow.add_widget(
            styled_button("Save key", size_hint_x=None, width=dp(100), on_release=self.save_key)
        )
        root.add_widget(keyrow)

        tabrow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.tablet_inp = styled_input("Tablet IP (e.g. 192.168.1.15 or 100.x.x.x)")
        self.tablet_inp.text = self.tablet_ip
        tabrow.add_widget(self.tablet_inp)
        tabrow.add_widget(
            styled_button("Save IP", size_hint_x=None, width=dp(90), on_release=self.save_tablet_ip)
        )
        root.add_widget(tabrow)

        self.refresh_buttons()
        return root

    # ---------- lifecycle ----------
    def on_start(self):
        if ANDROID:
            android_activity.bind(on_activity_result=self.on_activity_result)
            request_permissions(
                [
                    Permission.RECORD_AUDIO,
                    Permission.READ_CONTACTS,
                    Permission.CALL_PHONE,
                    Permission.SEND_SMS,
                    Permission.READ_PHONE_STATE,
                    Permission.READ_CALL_LOG,
                ]
            )
            self.init_tts()
            self.rec_listener = RecListener(self.sr_text_cb, self.sr_err_cb)
            self.start_call_watcher()
        self.say(self.brain.greeting())
        Clock.schedule_interval(self.housekeeping, 15)

    def on_pause(self):
        return True

    def on_stop(self):
        self.ui_sr_destroy()
        if self.call_receiver is not None:
            try:
                self.call_receiver.stop()
            except Exception:
                pass
        if self.tts is not None:
            try:
                self.tts.shutdown()
            except Exception:
                pass

    # ---------- settings ----------
    def save_settings(self):
        self.store.save(
            "mini_set.json",
            {
                "online": self.online,
                "proactive": self.proactive_on,
                "mood": self.brain.mood,
                "model": self.model,
                "cc": self.cc,
                "tablet_on": self.tablet_on,
                "tablet_ip": self.tablet_ip,
            },
        )

    def refresh_buttons(self):
        self.mode_btn.text = "ONLINE" if self.online else "OFFLINE"
        self.listen_btn.text = "LISTEN: " + ("ON" if self.always else "OFF")
        self.pro_btn.text = "PROACTIVE: " + ("ON" if self.proactive_on else "OFF")
        self.tablet_btn.text = "TABLET: " + ("ON" if self.tablet_on else "OFF")

    def save_tablet_ip(self, *_):
        ip = self.tablet_inp.text.strip()
        self.tablet_ip = ip
        self.save_settings()
        self.add("(Tablet IP saved: %s)" % (ip or "none"))

    def toggle_tablet(self, *_):
        self.wake()
        if not self.tablet_on and not self.tablet_ip:
            self.add("Set the tablet IP below first, then tap Save IP.")
            return
        self.tablet_on = not self.tablet_on
        self.save_settings()
        self.refresh_buttons()
        self.say(
            "Tablet mode on. I will send commands to mini Brain."
            if self.tablet_on
            else "Tablet mode off. I will process commands myself again."
        )

    def set_mode(self, online):
        self.online = online
        self.save_settings()
        self.refresh_buttons()
        if online:
            self.say("Online mode. I will use Gemini for chat and weather.")
        else:
            self.say("Offline mode. Phone commands only.")

    def toggle_mode(self, *_):
        self.wake()
        self.set_mode(not self.online)

    def toggle_pro(self, *_):
        self.wake()
        self.proactive_on = not self.proactive_on
        self.last_any = time.time()
        self.save_settings()
        self.refresh_buttons()
        self.say("Proactive on. I will talk if it is quiet for 5 minutes." if self.proactive_on else "Proactive off.")

    def save_key(self, *_):
        key = self.key_inp.text.strip()
        if not key:
            return
        self.store.write_text("gemini_key.txt", key)
        self.key_inp.text = ""
        self.add("(API key saved on this phone)")

    # ---------- ui helpers ----------
    def add(self, line):
        self.lines = (self.lines + [line])[-4:]
        self.log.text = "\n\n".join(self.lines)
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def set_state(self, state, hold=None):
        Clock.unschedule(self._idle)
        self.orb.state = state
        if hold:
            Clock.schedule_once(self._idle, hold)

    def _idle(self, dt=None):
        self.orb.state = "sleep" if self.asleep else "idle"

    def say(self, r):
        if isinstance(r, str):
            r = R(r)
        now = time.time()
        self.last_any = now
        self.add("mini: " + r.shown)
        hold = 0.8 + len(r.shown) * 0.06
        self.conv_until = now + hold + 20
        self.set_state("speaking", hold)
        self.speak(r)

    def on_send(self, *_):
        text = self.inp.text
        self.inp.text = ""
        self.handle(text)

    def is_speaking(self):
        if self.orb.state in ("speaking", "thinking"):
            return True
        try:
            return bool(self.tts is not None and self.tts.isSpeaking())
        except Exception:
            return False

    # ---------- sleep / wake ----------
    def wake(self):
        self.last_user = time.time()
        if self.asleep:
            self.asleep = False
            self.set_state("idle")

    def sleep_now(self, msg):
        self.stop_always()
        self.asleep = True
        self.set_state("sleep")
        if msg:
            self.say(msg)

    def housekeeping(self, dt):
        now = time.time()
        if now - self.last_clean > 3600:
            self.last_clean = now
            self.brain.mem.cleanup()
        if self.asleep:
            return
        if self.always and now - self.last_user > IDLE_SLEEP_SECONDS:
            return self.sleep_now("I am going to sleep. Tap the orb to wake me.")
        if self.proactive_on and now - self.last_any > PROACTIVE_SECONDS and not self.is_speaking():
            self.say(self.brain.proactive())

    # ---------- voice output ----------
    def init_tts(self):
        def on_init(status):
            if status == TextToSpeech.SUCCESS:
                try:
                    self.hi_ok = self.tts.setLanguage(Locale("hi", "IN")) >= 0
                    self.tts.setLanguage(Locale.US)
                except Exception:
                    self.hi_ok = False
                self.tts_ready = True
                if self.pending:
                    self.speak_now(self.pending)
                    self.pending = None
            else:
                Clock.schedule_once(lambda dt: self.add("(voice output not available)"))

        self.tts_listener = TTSInit(on_init)
        self.tts = TextToSpeech(PythonActivity.mActivity, self.tts_listener)

    def speak(self, r):
        if not ANDROID or self.tts is None:
            return
        if self.tts_ready:
            self.speak_now(r)
        else:
            self.pending = r

    def speak_now(self, r):
        try:
            deva = has_deva(r.spoken)
            if deva and not self.hi_ok:
                text, base = r.shown, "en"  # no Hindi voice installed: read Roman text
            else:
                text, base = r.spoken, ("hi" if deva else "en")
            text = re.sub(r"[*_#`]", "", text)
            first = True
            for lang, chunk in segments(text, base):
                self.tts.setLanguage(Locale("hi", "IN") if lang == "hi" else Locale.US)
                self.tts.speak(chunk, TextToSpeech.QUEUE_FLUSH if first else TextToSpeech.QUEUE_ADD, None)
                first = False
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda dt: self.add("(voice error: %s)" % msg))

    # ---------- voice input: SPEAK button (Google dialog) ----------
    def listen(self, *_):
        self.wake()
        if not ANDROID:
            self.add("Mic works only on Android.")
            return
        try:
            if self.always:
                Clock.unschedule(self.start_loop)
                self.ui_sr_stop()
            self.set_state("listening", 45)
            i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            i.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to mini")
            PythonActivity.mActivity.startActivityForResult(i, REQ_SPEECH)
        except Exception as e:
            self.set_state("idle")
            self.add("Voice error: %s" % e)

    def on_activity_result(self, request_code, result_code, intent):
        if request_code != REQ_SPEECH:
            return
        Clock.schedule_once(lambda dt: self.set_state("idle"))
        if self.always:
            Clock.schedule_once(lambda dt: self.loop_later(1.5))
        if result_code != -1 or intent is None:
            return
        lst = intent.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
        if lst is None or lst.size() == 0:
            return
        first = lst.get(0)
        text = first if isinstance(first, str) else first.toString()
        Clock.schedule_once(lambda dt: self.handle(text))

    # ---------- voice input: Always Listen (SpeechRecognizer loop) ----------
    def toggle_listen(self, *_):
        if not ANDROID:
            self.add("Always Listen works only on Android.")
            return
        self.wake()
        if self.always:
            self.stop_always()
            self.say("Always listen off.")
            return
        if not check_permission(Permission.RECORD_AUDIO):
            request_permissions([Permission.RECORD_AUDIO])
            self.say("Allow the microphone, then tap Listen again.")
            return
        self.always = True
        self.sr_fail = 0
        self.refresh_buttons()
        self.say("Always listen on. Say mini, then your command.")
        self.loop_later(2.5)

    def stop_always(self):
        self.always = False
        Clock.unschedule(self.start_loop)
        self.ui_sr_stop()
        self.refresh_buttons()

    def loop_later(self, delay):
        Clock.unschedule(self.start_loop)
        Clock.schedule_once(self.start_loop, delay)

    def start_loop(self, dt=None):
        if not (ANDROID and self.always) or self.asleep:
            return
        if self.is_speaking():
            Clock.schedule_once(self.start_loop, 0.8)
            return
        self.ui_sr_start()

    @run_on_ui_thread
    def ui_sr_start(self):
        try:
            if self.sr is None:
                self.sr = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)
                self.sr.setRecognitionListener(self.rec_listener)
            i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            self.sr.startListening(i)
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda dt: self.on_rec_error(5, msg))

    @run_on_ui_thread
    def ui_sr_stop(self):
        try:
            if self.sr is not None:
                self.sr.cancel()
        except Exception:
            pass

    @run_on_ui_thread
    def ui_sr_destroy(self):
        try:
            if self.sr is not None:
                self.sr.destroy()
        except Exception:
            pass
        self.sr = None

    def sr_text_cb(self, text):
        Clock.schedule_once(lambda dt: self.on_rec_result(text))

    def sr_err_cb(self, code):
        Clock.schedule_once(lambda dt: self.on_rec_error(code))

    def on_rec_result(self, text):
        self.sr_fail = 0
        if text and (WAKE.search(text.lower()) or time.time() < self.conv_until):
            self.handle(text)
        self.loop_later(0.6)

    def on_rec_error(self, code, msg=""):
        if not self.always:
            return
        if code == 9:
            self.stop_always()
            self.say("I need microphone permission for always listen.")
            return
        if code in (6, 7):  # silence / no match: just listen again
            self.loop_later(0.3)
            return
        self.sr_fail += 1
        if self.sr_fail >= 5:
            self.stop_always()
            self.say("Always listen stopped. Microphone error %s. %s" % (code, msg))
            return
        self.ui_sr_destroy()
        self.loop_later(1.5)

    # ---------- command handling ----------
    def handle(self, text):
        t = text.strip()
        if not t:
            return
        self.wake()

        if self.tablet_on:
            self.add("You: " + t)
            self.set_state("thinking", 30)
            threading.Thread(target=self.tablet_worker, args=(t,), daemon=True).start()
            return

        kind, p = self.brain.route(t)
        if kind in ("vault_save", "vault_get"):
            self.add("You: (password command)")
        elif kind != "empty":
            self.add("You: " + t)
        self.save_settings()

        if kind in ("say", "vault_save", "vault_get"):
            self.say(p)
        elif kind == "stop":
            self.sleep_now(None)
            self.say(p)
        elif kind == "off":
            self.say(p)
            Clock.schedule_once(lambda dt: self.stop(), 2.5)
        elif kind == "online":
            self.set_mode(p)
        elif kind == "model":
            self.model = p
            self.save_settings()
            self.say("Model set to %s." % p)
        elif kind == "cc":
            self.cc = p
            self.save_settings()
            self.say("Country code set to plus %s." % p)
        elif kind == "call":
            self.say(self.act_call(p))
        elif kind == "open":
            self.say(self.act_open(p))
        elif kind == "search":
            self.act_search(p)
        elif kind == "whatsapp":
            self.say(self.act_whatsapp(p))
        elif kind == "torch":
            self.say(self.act_torch(p))
        elif kind == "volume":
            self.say(self.act_volume(p))
        elif kind == "settings":
            self.say(self.act_settings(p))
        elif kind == "battery":
            self.say(self.act_battery())
        elif kind == "sms":
            self.say(self.act_sms(*p))
        elif kind == "weather":
            self.act_weather(*p)
        elif kind == "ai":
            if self.online:
                self.ask_ai(p)
            else:
                self.say("I am offline. Switch to online mode for chat.")

    # ---------- tablet mode (mini Brain) ----------
    def tablet_worker(self, text):
        try:
            resp = call_tablet(self.tablet_ip, text)
        except Exception as e:
            msg = "I cannot reach mini Brain on the tablet: %s" % e
            Clock.schedule_once(lambda dt: self.say(msg))
            return
        Clock.schedule_once(lambda dt: self.dispatch_tablet_action(resp))

    def dispatch_tablet_action(self, resp):
        action = resp.get("action")
        spoken = resp.get("spoken", "")
        shown = resp.get("shown", spoken)
        if action == "say":
            self.say(R(spoken, shown))
        elif action == "stop":
            self.sleep_now(None)
            self.say(R(spoken, shown))
        elif action == "off":
            self.say(R(spoken, shown))
            Clock.schedule_once(lambda dt: self.stop(), 2.5)
        elif action == "call":
            self.say(self.act_call(resp.get("target", "")))
        elif action == "open":
            self.say(self.act_open(resp.get("target", "")))
        elif action == "whatsapp":
            self.say(self.act_whatsapp(resp.get("target", "")))
        elif action == "torch":
            self.say(self.act_torch(bool(resp.get("on"))))
        elif action == "volume":
            self.say(self.act_volume(resp.get("mode", "")))
        elif action == "settings":
            self.say(self.act_settings(resp.get("page", "settings")))
        elif action == "battery":
            self.say(self.act_battery())
        elif action == "sms":
            self.say(self.act_sms(resp.get("target", ""), resp.get("text", "")))
        elif action == "search":
            self.finish_search(resp.get("query", ""), None)
        else:
            self.say("I got an unexpected reply from mini Brain.")

    # ---------- phone actions ----------
    def start_activity(self, intent):
        PythonActivity.mActivity.startActivity(intent)

    # ---------- caller announcement ----------
    def start_call_watcher(self):
        try:
            from android.broadcast import BroadcastReceiver

            self.call_receiver = BroadcastReceiver(
                self.on_phone_broadcast, actions=["android.intent.action.PHONE_STATE"]
            )
            self.call_receiver.start()
        except Exception as e:
            msg = str(e)
            Clock.schedule_once(lambda dt: self.add("(call announcement unavailable: %s)" % msg))

    def on_phone_broadcast(self, context, intent):
        try:
            state = intent.getStringExtra("state")
            number = intent.getStringExtra("incoming_number")
        except Exception:
            return
        Clock.schedule_once(lambda dt: self.handle_call_state(state, number))

    def handle_call_state(self, state, number):
        if state != "RINGING":
            if state == "IDLE":
                self.last_call_key = None
            return
        key = number or "unknown"
        if key == self.last_call_key:
            return
        self.last_call_key = key
        if not number:
            return self.say("Someone is calling, but I could not read the number.")
        try:
            name = find_name(number)
        except Exception:
            name = None
        if name:
            self.say("%s is calling." % name)
        else:
            self.say("An unknown number is calling: " + " ".join(number))

    def need_contacts(self, need_call=False):
        perms = [Permission.READ_CONTACTS] + ([Permission.CALL_PHONE] if need_call else [])
        if all(check_permission(p) for p in perms):
            return False
        request_permissions(perms)
        return True

    def act_call(self, name):
        if not ANDROID:
            return "Calling works only on the phone."
        if self.need_contacts(True):
            return "I need contacts and phone permission. Allow it, then say that again."
        try:
            number = find_number(name)
            if not number:
                return "I could not find %s in your contacts." % name
            self.start_activity(Intent(Intent.ACTION_CALL, Uri.parse("tel:" + number)))
            return "Calling %s." % name
        except Exception as e:
            return "Call failed: %s" % e

    def act_whatsapp(self, name):
        if not ANDROID:
            return "WhatsApp works only on the phone."
        if self.need_contacts():
            return "I need contacts permission. Allow it, then say that again."
        try:
            number = find_number(name)
            if not number:
                return "I could not find %s in your contacts." % name
            if not number.startswith("+"):
                number = "+" + self.cc + number.lstrip("0")
            i = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/" + number.lstrip("+")))
            i.setPackage("com.whatsapp")
            self.start_activity(i)
            return "Opening WhatsApp chat with %s." % name
        except Exception as e:
            return "WhatsApp failed: %s" % e

    def act_torch(self, on):
        if not ANDROID:
            return "Torch works only on the phone."
        try:
            cm = cast("android.hardware.camera2.CameraManager", PythonActivity.mActivity.getSystemService(Context.CAMERA_SERVICE))
            ids = cm.getCameraIdList()
            cam_id = ids[0] if isinstance(ids, str) else ids[0]
            cm.setTorchMode(cam_id, on)
            return "Torch on." if on else "Torch off."
        except Exception as e:
            return "Torch failed: %s" % e

    def act_volume(self, action):
        if not ANDROID:
            return "Volume control works only on the phone."
        try:
            am = cast("android.media.AudioManager", PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE))
            stream = AudioManager.STREAM_MUSIC
            flag = AudioManager.FLAG_SHOW_UI
            if action == "up":
                am.adjustStreamVolume(stream, AudioManager.ADJUST_RAISE, flag)
                return "Volume up."
            if action == "down":
                am.adjustStreamVolume(stream, AudioManager.ADJUST_LOWER, flag)
                return "Volume down."
            if action == "mute":
                am.adjustStreamVolume(stream, AudioManager.ADJUST_MUTE, flag)
                return "Muted."
            if action == "unmute":
                am.adjustStreamVolume(stream, AudioManager.ADJUST_UNMUTE, flag)
                return "Unmuted."
            if action == "max":
                top = am.getStreamMaxVolume(stream)
                am.setStreamVolume(stream, top, flag)
                return "Volume at maximum."
        except Exception as e:
            return "Volume failed: %s" % e
        return "I did not understand that volume command."

    def act_settings(self, page):
        if not ANDROID:
            return "Settings works only on the phone."
        actions = {
            "wifi": (Settings.ACTION_WIFI_SETTINGS, "Wi-Fi settings."),
            "bluetooth": (Settings.ACTION_BLUETOOTH_SETTINGS, "Bluetooth settings."),
            "settings": (Settings.ACTION_SETTINGS, "Settings."),
        }
        action, msg = actions[page]
        try:
            self.start_activity(Intent(action))
            return "Opening " + msg
        except Exception as e:
            return "Could not open settings: %s" % e

    def act_battery(self):
        if not ANDROID:
            return "Battery check works only on the phone."
        try:
            act = PythonActivity.mActivity
            info = act.registerReceiver(None, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            level = info.getIntExtra("level", -1)
            scale = info.getIntExtra("scale", -1)
            if level < 0 or scale <= 0:
                return "I could not read the battery level."
            pct = round(level * 100.0 / scale)
            return "Battery is at %d percent." % pct
        except Exception as e:
            return "Battery check failed: %s" % e

    def act_sms(self, name, text):
        if not ANDROID:
            return "Sending messages works only on the phone."
        if self.need_contacts() or not check_permission(Permission.SEND_SMS):
            request_permissions([Permission.READ_CONTACTS, Permission.SEND_SMS])
            return "I need contacts and SMS permission. Allow it, then say that again."
        try:
            number = find_number(name)
            if not number:
                return "I could not find %s in your contacts." % name
            sms = SmsManager.getDefault()
            sms.sendTextMessage(number, None, text, None, None)
            return "Message sent to %s." % name
        except Exception as e:
            return "Message failed: %s" % e

    def act_open(self, name):
        if not ANDROID:
            return "Opening apps works only on the phone."
        try:
            pm = PythonActivity.mActivity.getPackageManager()
            i = Intent(Intent.ACTION_MAIN)
            i.addCategory(Intent.CATEGORY_LAUNCHER)
            apps = pm.queryIntentActivities(i, 0)
            for k in range(apps.size()):
                ri = cast("android.content.pm.ResolveInfo", apps.get(k))
                raw_label = ri.loadLabel(pm)
                label = (raw_label if isinstance(raw_label, str) else raw_label.toString()).lower()
                if name in label:
                    self.start_activity(pm.getLaunchIntentForPackage(ri.activityInfo.packageName))
                    return "Opening %s." % label
            for pkg in APP_ALIASES.get(name, []):
                li = pm.getLaunchIntentForPackage(pkg)
                if li is not None:
                    self.start_activity(li)
                    return "Opening %s." % name
            return "I could not find an app called %s." % name
        except Exception as e:
            return "Open failed: %s" % e

    def act_search(self, query):
        if not ANDROID:
            return self.say("Search works only on the phone.")
        self.set_state("thinking", 30)

        def worker():
            answer = None
            try:
                answer = fetch_instant_answer(query)
            except Exception:
                answer = None
            Clock.schedule_once(lambda dt: self.finish_search(query, answer))

        threading.Thread(target=worker, daemon=True).start()

    def finish_search(self, query, answer):
        if answer:
            return self.say(answer)
        try:
            url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            self.start_activity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            self.say("I could not find a direct answer, so I opened a search for %s." % query)
        except Exception as e:
            self.say("Search failed: %s" % e)

    # ---------- weather (online) ----------
    def act_weather(self, lang, city):
        if not self.online:
            return self.say("Weather needs internet. Switch to online mode.")
        self.set_state("thinking", 30)

        def worker():
            try:
                temp, unit, cond = fetch_weather(city)
                r = self.brain.weather_reply(lang, temp, unit, cond)
                Clock.schedule_once(lambda dt, x=r: self.say(x))
            except Exception:
                Clock.schedule_once(lambda dt: self.say("I could not get the weather right now."))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Gemini (online mode) ----------
    def ask_ai(self, text):
        key = self.store.read_text("gemini_key.txt")
        if not key:
            return self.say("Paste your Gemini API key below and tap Save key.")
        self.history.append({"role": "user", "parts": [{"text": text}]})
        self.history = self.history[-11:]
        while self.history and self.history[0]["role"] != "user":
            self.history.pop(0)
        contents = list(self.history)
        model = self.model
        system = self.brain.system_prompt()
        self.set_state("thinking", 60)

        def worker():
            try:
                reply = call_gemini(key, model, system, contents)
                Clock.schedule_once(lambda dt, r=reply: self.on_ai(r))
            except urllib.error.HTTPError as e:
                if e.code in (400, 403):
                    msg = "Google rejected the request. Check your API key."
                elif e.code == 404:
                    msg = "Model not found. Type: use model gemini-3.1-flash-lite"
                elif e.code == 429:
                    msg = "Too many requests. Wait a minute and try again."
                else:
                    msg = "AI error %s." % e.code
                Clock.schedule_once(lambda dt, m=msg: self.on_ai_fail(m))
            except Exception as e:
                msg = "AI error: %s" % e
                Clock.schedule_once(lambda dt, m=msg: self.on_ai_fail(m))

        threading.Thread(target=worker, daemon=True).start()

    def on_ai(self, reply):
        if not reply:
            return self.say("I have no answer for that.")
        self.history.append({"role": "model", "parts": [{"text": reply}]})
        self.say(self.brain.parse_ai(reply))

    def on_ai_fail(self, msg):
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        self.say(msg)


if __name__ == "__main__":
    Mini().run()
