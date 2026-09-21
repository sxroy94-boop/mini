"""mini - Android voice assistant (always listening + proactive mode)."""
import datetime
import json
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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform

try:
    import certifi
except Exception:
    certifi = None

ANDROID = platform == "android"
MODEL = "gemini-1.5-flash"
SYSTEM = (
    "You are mini, a friendly AI voice assistant on an Android phone. "
    "Reply in 1-2 short spoken sentences. No markdown, no lists, no emojis."
)
PROACTIVE_SYSTEM = (
    "You are mini. Boss has been quiet for a while. "
    "Start a short friendly conversation in 1 sentence. "
    "Ask something personal, share a small thought, or tell a tiny fun fact. "
    "Keep it natural. No markdown, no emojis."
)
SLEEP_TIMEOUT = 900        # 15 min silence -> sleep mode
PROACTIVE_TIMEOUT = 300    # 5 min silence (while online) -> mini talks itself

if ANDROID:
    from android import activity as android_activity
    from android.permissions import Permission, check_permission, request_permissions
    from jnius import PythonJavaClass, autoclass, cast, java_method

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    Locale = autoclass("java.util.Locale")

    class TTSInit(PythonJavaClass):
        __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
        __javacontext__ = "app"

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method("(I)V")
        def onInit(self, status):
            self.callback(status)

    class SpeechListener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/RecognitionListener"]
        __javacontext__ = "app"

        def __init__(self, on_result, on_error):
            super().__init__()
            self.on_result = on_result
            self.on_error = on_error

        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params): pass

        @java_method("()V")
        def onBeginningOfSpeech(self): pass

        @java_method("(F)V")
        def onRmsChanged(self, rms): pass

        @java_method("([B)V")
        def onBufferReceived(self, buf): pass

        @java_method("()V")
        def onEndOfSpeech(self): pass

        @java_method("(I)V")
        def onError(self, error):
            self.on_error(error)

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            try:
                matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if matches is not None and matches.size() > 0:
                    text = matches.get(0)
                    text = text if isinstance(text, str) else text.toString()
                    self.on_result(text)
                    return
            except Exception:
                pass
            self.on_result("")

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partial): pass

        @java_method("(Landroid/os/Bundle;)V")
        def onEvent(self, eventType, params): pass


def call_gemini(key, messages, system=SYSTEM):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    ctx = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
        out = json.loads(r.read().decode())
    try:
        return out["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "Sorry, I could not get an answer."


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


class Mini(App):
    title = "mini"

    def build(self):
        Window.softinput_mode = "below_target"
        self.history = []
        self.tts = None
        self.tts_ready = False
        self.pending = None
        self.mode = "offline"
        self.always_listen = False
        self.is_sleeping = True
        self.last_active = time.time()
        self.last_proactive = time.time()
        self.speech = None
        self.speech_listener = None
        self.recognition_running = False
        self.suppress_restart = False
        self.hard_off = False

        root = BoxLayout(orientation="vertical", padding=10, spacing=6)

        # Mode toggle
        self.mode_btn = Button(
            text="MODE: OFFLINE",
            size_hint_y=None, height=50, font_size="15sp",
            background_color=(0.2, 0.6, 0.2, 1),
        )
        self.mode_btn.bind(on_release=self.toggle_mode)
        root.add_widget(self.mode_btn)

        # Always listen toggle
        self.listen_btn = Button(
            text="ALWAYS LISTEN: OFF",
            size_hint_y=None, height=50, font_size="15sp",
            background_color=(0.5, 0.2, 0.2, 1),
        )
        self.listen_btn.bind(on_release=self.toggle_always_listen)
        root.add_widget(self.listen_btn)

        # Proactive toggle
        self.proactive_btn = Button(
            text="PROACTIVE: OFF",
            size_hint_y=None, height=50, font_size="15sp",
            background_color=(0.3, 0.3, 0.5, 1),
        )
        self.proactive_btn.bind(on_release=self.toggle_proactive)
        self.proactive_on = False
        root.add_widget(self.proactive_btn)

        self.scroll = ScrollView()
        self.log = Label(size_hint_y=None, halign="left", valign="top", font_size="14sp")
        self.log.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        self.log.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.scroll.add_widget(self.log)
        root.add_widget(self.scroll)

        row = BoxLayout(size_hint_y=None, height=42, spacing=6)
        self.inp = TextInput(hint_text="Type a command", multiline=False)
        self.inp.bind(on_text_validate=self.on_send)
        row.add_widget(self.inp)
        row.add_widget(Button(text="Send", size_hint_x=None, width=80, on_release=self.on_send))
        root.add_widget(row)

        root.add_widget(
            Button(text="SPEAK NOW", size_hint_y=None, height=60, font_size="18sp", on_release=self.manual_speak)
        )

        keyrow = BoxLayout(size_hint_y=None, height=42, spacing=6)
        self.key_inp = TextInput(hint_text="Gemini API key", password=True, multiline=False)
        keyrow.add_widget(self.key_inp)
        keyrow.add_widget(Button(text="Save key", size_hint_x=None, width=100, on_release=self.save_key))
        root.add_widget(keyrow)
        return root

    # ---------- mode toggle ----------
    def toggle_mode(self, *_):
        if self.mode == "offline":
            if not self.load_key():
                self.add("(Online mode needs Gemini API key. Save key first.)")
                return
            self.mode = "online"
            self.mode_btn.text = "MODE: ONLINE"
            self.mode_btn.background_color = (0.2, 0.4, 0.8, 1)
            self.last_proactive = time.time()
            self.say("Online mode on.")
        else:
            self.mode = "offline"
            self.mode_btn.text = "MODE: OFFLINE"
            self.mode_btn.background_color = (0.2, 0.6, 0.2, 1)
            self.say("Offline mode on.")

    # ---------- always listen toggle ----------
    def toggle_always_listen(self, *_):
        if not ANDROID:
            self.add("Always listen works only on Android.")
            return
        if not self.always_listen:
            self.always_listen = True
            self.is_sleeping = True
            self.listen_btn.text = "ALWAYS LISTEN: ON"
            self.listen_btn.background_color = (0.2, 0.7, 0.2, 1)
            self.add("(Always listen ON. Say 'mini' to wake.)")
            self.speak("Always listening on. Say mini to wake me.")
            self.start_speech_loop()
        else:
            self.always_listen = False
            self.listen_btn.text = "ALWAYS LISTEN: OFF"
            self.listen_btn.background_color = (0.5, 0.2, 0.2, 1)
            self.stop_speech_loop()
            self.add("(Always listen OFF)")

    # ---------- proactive toggle ----------
    def toggle_proactive(self, *_):
        if not self.proactive_on:
            if self.mode != "online":
                self.add("(Proactive needs Online mode.)")
                return
            self.proactive_on = True
            self.proactive_btn.text = "PROACTIVE: ON"
            self.proactive_btn.background_color = (0.2, 0.7, 0.4, 1)
            self.last_proactive = time.time()
            self.say("Proactive mode on. I will talk to you sometimes.")
        else:
            self.proactive_on = False
            self.proactive_btn.text = "PROACTIVE: OFF"
            self.proactive_btn.background_color = (0.3, 0.3, 0.5, 1)
            self.say("Proactive mode off.")

    # ---------- lifecycle ----------
    def on_start(self):
        if ANDROID:
            android_activity.bind(on_activity_result=self.on_activity_result)
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.READ_CONTACTS,
                Permission.CALL_PHONE,
            ])
            self.init_tts()
            Clock.schedule_interval(self.tick, 20)
        self.say("Hello Boss! I am mini. Offline mode. Tap ALWAYS LISTEN to enable wake word.")

    def on_pause(self):
        return True

    def on_stop(self):
        self.stop_speech_loop()
        if self.tts is not None:
            try:
                self.tts.shutdown()
            except Exception:
                pass

    # ---------- tick: sleep + proactive ----------
    def tick(self, dt):
        now = time.time()
        # Sleep mode check
        if self.always_listen and not self.is_sleeping:
            if now - self.last_active > SLEEP_TIMEOUT:
                self.is_sleeping = True
                self.add("(sleeping - say 'mini')")
                self.speak("Going to sleep.")
        # Proactive check
        if (self.proactive_on and self.mode == "online"
                and not self.is_sleeping
                and now - self.last_proactive > PROACTIVE_TIMEOUT
                and now - self.last_active > PROACTIVE_TIMEOUT):
            self.last_proactive = now
            self.speak_proactive()

    def speak_proactive(self):
        key = self.load_key()
        if not key:
            return
        prompts = [
            "Start a short friendly sentence to Boss.",
            "Ask Boss how his day is going.",
            "Share a tiny interesting fact.",
            "Say something warm and personal.",
            "Ask Boss what he is doing right now.",
        ]
        msg = [{"role": "user", "content": random.choice(prompts)}]
        self.add("(mini is thinking of something to say...)")

        def worker():
            try:
                reply = call_gemini(key, msg, system=PROACTIVE_SYSTEM)
                Clock.schedule_once(lambda dt, r=reply: self.on_proactive_reply(r))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def on_proactive_reply(self, reply):
        if reply:
            self.say(reply)

    # ---------- speech loop ----------
    def start_speech_loop(self):
        if not ANDROID:
            return
        try:
            if self.speech is None:
                self.speech = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)
                self.speech_listener = SpeechListener(self.on_speech_result, self.on_speech_error)
                self.speech.setRecognitionListener(self.speech_listener)
            self.schedule_restart(0.3)
        except Exception as e:
            self.add("Speech init error: %s" % e)

    def stop_speech_loop(self):
        self.suppress_restart = True
        try:
            if self.speech is not None:
                self.speech.stopListening()
                self.speech.cancel()
        except Exception:
            pass
        self.recognition_running = False

    def schedule_restart(self, delay=0.5):
        if not self.always_listen or self.suppress_restart or self.hard_off:
            return
        Clock.schedule_once(lambda dt: self.begin_listening(), delay)

    def begin_listening(self):
        if not self.always_listen or self.suppress_restart or self.hard_off:
            return
        try:
            i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
            i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            self.speech.startListening(i)
            self.recognition_running = True
        except Exception as e:
            self.add("Listen error: %s" % e)
            self.schedule_restart(2)

    def on_speech_error(self, error):
        self.recognition_running = False
        self.schedule_restart(0.4)

    def on_speech_result(self, text):
        self.recognition_running = False
        if not text:
            self.schedule_restart(0.4)
            return

        t = text.strip()
        low = t.lower()

        # Hard off check
        if "mini off" in low or "mic off" in low or "mini band" in low:
            self.hard_off = True
            self.always_listen = False
            self.stop_speech_loop()
            self.speak("Mic off. Goodbye boss.")
            self.add("(Hard off - tap ALWAYS LISTEN to restart)")
            return

        # Sleep mode: wait for wake word
        if self.is_sleeping:
            if "mini" in low or "hey mini" in low:
                self.is_sleeping = False
                self.last_active = time.time()
                self.last_proactive = time.time()
                self.speak("Yes boss?")
                self.add("mini: (awake) Yes boss?")
            self.schedule_restart(0.4)
            return

        self.last_active = time.time()
        self.last_proactive = time.time()
        low = low.replace("hey mini", "").replace("mini", "").strip(" ,.!?")
        if not low:
            self.schedule_restart(0.4)
            return

        Clock.schedule_once(lambda dt: self.handle(low))
        self.schedule_restart(1.2)

    # ---------- manual speak ----------
    def manual_speak(self, *_):
        if not ANDROID:
            self.add("Mic works only on Android.")
            return
        try:
            i = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            i.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to mini")
            PythonActivity.mActivity.startActivityForResult(i, 4242)
        except Exception as e:
            self.add("Voice error: %s" % e)

    def on_activity_result(self, request_code, result_code, intent):
        if request_code != 4242 or result_code != -1 or intent is None:
            return
        lst = intent.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
        if lst is None or lst.size() == 0:
            return
        first = lst.get(0)
        text = first if isinstance(first, str) else first.toString()
        Clock.schedule_once(lambda dt: self.handle(text))

    # ---------- ui ----------
    def add(self, line):
        self.log.text += line + "\n\n"
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def say(self, text):
        self.add("mini: " + text)
        self.speak(text)

    def on_send(self, *_):
        text = self.inp.text
        self.inp.text = ""
        self.handle(text)

    # ---------- key ----------
    def key_path(self):
        return os.path.join(self.user_data_dir, "gemini_key.txt")

    def load_key(self):
        try:
            with open(self.key_path()) as f:
                return f.read().strip()
        except Exception:
            return ""

    def save_key(self, *_):
        key = self.key_inp.text.strip()
        if not key:
            return
        with open(self.key_path(), "w") as f:
            f.write(key)
        self.key_inp.text = ""
        self.add("(Gemini API key saved)")

    # ---------- tts ----------
    def init_tts(self):
        def on_init(status):
            if status == TextToSpeech.SUCCESS:
                self.tts.setLanguage(Locale.US)
                self.tts_ready = True
                if self.pending:
                    self.tts.speak(self.pending, TextToSpeech.QUEUE_FLUSH, None)
                    self.pending = None

        self.tts_listener = TTSInit(on_init)
        self.tts = TextToSpeech(PythonActivity.mActivity, self.tts_listener)

    def speak(self, text):
        if not ANDROID or self.tts is None:
            return
        clean = re.sub(r"[*_#`]", "", text)
        if self.tts_ready:
            self.tts.speak(clean, TextToSpeech.QUEUE_FLUSH, None)
        else:
            self.pending = clean

    # ---------- command handler ----------
    def handle(self, text):
        t = text.strip()
        if not t:
            return
        self.add("You: " + t)
        low = t.lower().strip(" .!?")

        # Hard off
        if "mini off" in low or "mic off" in low:
            self.hard_off = True
            self.always_listen = False
            self.stop_speech_loop()
            return self.say("Mic off. Goodbye boss.")

        # Mode switch
        if "online mode" in low or "online mood" in low:
            self.mode = "online"
            self.mode_btn.text = "MODE: ONLINE"
            self.mode_btn.background_color = (0.2, 0.4, 0.8, 1)
            self.last_proactive = time.time()
            return self.say("Online mode on.")
        if "offline mode" in low or "offline mood" in low:
            self.mode = "offline"
            self.mode_btn.text = "MODE: OFFLINE"
            self.mode_btn.background_color = (0.2, 0.6, 0.2, 1)
            return self.say("Offline mode on.")

        # Proactive switch
        if "proactive on" in low or "proactive mood on" in low:
            if self.mode != "online":
                return self.say("Proactive needs online mode.")
            self.proactive_on = True
            self.proactive_btn.text = "PROACTIVE: ON"
            self.proactive_btn.background_color = (0.2, 0.7, 0.4, 1)
            self.last_proactive = time.time()
            return self.say("Proactive mode on.")
        if "proactive off" in low or "proactive mood off" in low:
            self.proactive_on = False
            self.proactive_btn.text = "PROACTIVE: OFF"
            self.proactive_btn.background_color = (0.3, 0.3, 0.5, 1)
            return self.say("Proactive mode off.")

        # Offline commands
        m = re.match(r"^(?:call|phone|dial)\s+(.+)$", low)
        if m:
            return self.say(self.act_call(m.group(1)))
        m = re.match(r"^(?:open|launch|start)\s+(.+)$", low)
        if m:
            return self.say(self.act_open(m.group(1)))
        m = re.match(r"^(?:search|google)(?: for)?\s+(.+)$", low)
        if m:
            return self.say(self.act_search(m.group(1)))
        if re.fullmatch(r"(what(?:'s| is)? the time|what time is it|time)", low):
            return self.say(datetime.datetime.now().strftime("It is %I:%M %p."))

        if self.mode == "offline":
            return self.say("Offline mode. Say 'online mode' for chat.")
        self.ask_ai(t)

    def act_call(self, name):
        if not ANDROID:
            return "Calling works only on phone."
        if not (check_permission(Permission.READ_CONTACTS) and check_permission(Permission.CALL_PHONE)):
            request_permissions([Permission.READ_CONTACTS, Permission.CALL_PHONE])
            return "Grant contacts and phone permission, then try again."
        try:
            number = find_number(name)
            if not number:
                return "I could not find %s." % name
            PythonActivity.mActivity.startActivity(Intent(Intent.ACTION_CALL, Uri.parse("tel:" + number)))
            return "Calling %s." % name
        except Exception as e:
            return "Call failed: %s" % e

    def act_open(self, name):
        if not ANDROID:
            return "Opening apps works only on phone."
        try:
            act = PythonActivity.mActivity
            pm = act.getPackageManager()
            i = Intent(Intent.ACTION_MAIN)
            i.addCategory(Intent.CATEGORY_LAUNCHER)
            apps = pm.queryIntentActivities(i, 0)
            for k in range(apps.size()):
                ri = cast("android.content.pm.ResolveInfo", apps.get(k))
                label = ri.loadLabel(pm).toString().lower()
                if name in label:
                    act.startActivity(pm.getLaunchIntentForPackage(ri.activityInfo.packageName))
                    return "Opening %s." % label
            return "No app called %s." % name
        except Exception as e:
            return "Open failed: %s" % e

    def act_search(self, query):
        if not ANDROID:
            return "Search works only on phone."
        try:
            url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            PythonActivity.mActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            return "Searching for %s." % query
        except Exception as e:
            return "Search failed: %s" % e

    # ---------- gemini ----------
    def ask_ai(self, text):
        key = self.load_key()
        if not key:
            return self.say("Save Gemini API key first.")
        self.history.append({"role": "user", "content": text})
        self.history = self.history[-11:]
        while self.history and self.history[0]["role"] != "user":
            self.history.pop(0)
        msgs = list(self.history)
        self.add("(thinking...)")

        def worker():
            try:
                reply = call_gemini(key, msgs)
                Clock.schedule_once(lambda dt, r=reply: self.on_ai(r))
            except urllib.error.HTTPError as e:
                msg = "AI error %s." % e.code
                Clock.schedule_once(lambda dt, m=msg: self.on_ai_fail(m))
            except Exception as e:
                msg = "AI error: %s" % e
                Clock.schedule_once(lambda dt, m=msg: self.on_ai_fail(m))

        threading.Thread(target=worker, daemon=True).start()

    def on_ai(self, reply):
        self.history.append({"role": "assistant", "content": reply})
        self.say(reply or "No answer.")

    def on_ai_fail(self, msg):
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        self.say(msg)


if __name__ == "__main__":
    Mini().run()
