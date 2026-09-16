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
    """App kholbe"""
    try:
        subprocess.run(["termux-open", app], timeout=5)
        return True
    except:
        return False

def app_control(q):
    apps = {
        "chrome": "com.android.chrome",
        "youtube": "com.google.android.youtube",
        "whatsapp": "com.whatsapp",
        "facebook": "com.facebook.katana",
        "instagram": "com.instagram.android",
        "telegram": "org.telegram.messenger",
        "camera": "com.android.camera",
        "gallery": "com.android.gallery3d",
        "settings": "com.android.settings",
        "google": "com.google.android.googlequicksearchbox",
        "gmail": "com.google.android.gm",
        "maps": "com.google.android.apps.maps",
        "play store": "com.android.vending",
        "spotify": "com.spotify.music",
        "netflix": "com.netflix.mediaclient",
        "vlc": "org.videolan.vlc",
        "phonepe": "com.phonepe.app",
        "paytm": "net.one97.paytm",
        "gpay": "com.google.android.apps.nbu.paisa.user",
        "zomato": "com.application.zomato",
        "swiggy": "in.swiggy.android",
        "flipkart": "com.flipkart.android",
        "amazon": "in.amazon.mShop.android.shopping",
    }
    for name, pkg in apps.items():
        if name in q:
            if open_app(pkg):
                return "Opening " + name + " boss!"
            return "Sorry, " + name + " open nahi ho paya."
    return None

def smart_home(q):
    if "light on" in q: return "Light on kar diya boss!"
    if "light off" in q: return "Light off kar diya boss!"
    if "fan on" in q: return "Fan on kar diya boss!"
    if "fan off" in q: return "Fan off kar diya boss!"
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
    sh = smart_home(q)
    if sh:
        print("Mini:", sh)
        bolo(sh, "hi")
        continue
    mc = mem_check(q)
    if mc:
        print("Mini:", mc)
        bolo(mc, "en")
        continue
    a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)