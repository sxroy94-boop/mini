import os
import subprocess
import datetime
import json

def bolo(t, b="hi"):
    os.system(f"termux-tts-speak -l {b} \"{t}\"")

def shono():
    print("Bolo...")
    r = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=15)
    t = r.stdout.strip().lower()
    if not t or "error" in t:
        return ""
    return t

MEM = "mini_mem.json"

def lm():
    try:
        with open(MEM) as f: return json.load(f)
    except: return {}

def sm(m):
    with open(MEM, "w") as f: json.dump(m, f)

def rem(k, v):
    m = lm()
    m[k] = {"v": v, "t": datetime.datetime.now().isoformat()}
    sm(m)

def rec(k):
    m = lm()
    return m[k]["v"] if k in m else None

def open_app(app):
    try:
        cmd = ["am", "start", "-a", "android.intent.action.MAIN", "-n", app]
        subprocess.run(cmd, timeout=5)
        return True
    except:
        return False

def app_control(q):
    apps = {
        "chrome": "com.android.chrome/com.google.android.apps.chrome.Main",
        "youtube": "com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity",
        "whatsapp": "com.whatsapp/com.whatsapp.Main",
        "camera": "com.android.camera/com.android.camera.CameraActivity",
        "settings": "com.android.settings/com.android.settings.Settings",
        "google": "com.google.android.googlequicksearchbox/com.google.android.launcher.GEL",
        "gmail": "com.google.android.gm/com.google.android.gm.ConversationListActivityGmail",
        "maps": "com.google.android.apps.maps/com.google.android.maps.MapsActivity",
        "play store": "com.android.vending/com.google.android.finsky.activities.MainActivity",
        "facebook": "com.facebook.katana/com.facebook.katana.LoginActivity",
        "instagram": "com.instagram.android/com.instagram.android.activity.MainTabActivity",
        "telegram": "org.telegram.messenger/org.telegram.ui.LaunchActivity",
    }
    for name, pkg in apps.items():
        if name in q:
            if open_app(pkg):
                return "Opening " + name + " boss!"
            return "Sorry, " + name + " open nahi ho paya."
    return None

def mem_check(q):
    if "call me" in q:
        n = q.split("call me")[-1].strip()
        rem("nick", n)
        return "Ok, I will call you " + n
    if "my password is" in q:
        pw = q.split("my password is")[-1].strip()
        rem("pwd", pw)
        return "Password saved."
    if "what is my password" in q:
        pw = rec("pwd")
        if pw: return "Your password is " + pw
        return "No password saved."
    return None

def buddhi(q):
    n = rec("nick") or "boss"
    if "hello" in q or "hi" in q:
        return "Hello " + n + "! Kaise ho?", "hi"
    if "kaise" in q: return "Main theek hoon!", "hi"
    return "Sorry, I did not understand.", "en"

n = rec("nick") or "boss"
bolo("Welcome back " + n + "!", "en")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "bye" in q or "stop" in q or "band" in q:
        bolo("Bye boss!", "en")
        break
    ap = app_control(q)
    if ap:
        print("Mini:", ap)
        bolo(ap, "en")
        continue
    mc = mem_check(q)
    if mc:
        print("Mini:", mc)
        bolo(mc, "en")
        continue
    a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)