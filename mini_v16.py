import os, subprocess, datetime, json

def bolo(t, b="en"):
    os.system(f'termux-tts-speak -l {b} "{t}"')

def shono():
    print("Bolo...")
    r = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=15)
    t = r.stdout.strip().lower()
    return t if t and "error" not in t else ""

MEM = "mini_mem.json"
def lm():
    try:
        with open(MEM) as f: return json.load(f)
    except: return {}
def sm(m):
    with open(MEM, "w") as f: json.dump(m, f)
def rem(k, v):
    m = lm(); m[k] = {"v": v, "t": datetime.datetime.now().isoformat()}; sm(m)
def rec(k):
    m = lm(); return m[k]["v"] if k in m else None

def open_app_by_name(app_name):
    app_name = app_name.lower().strip()
    if any(x in app_name for x in ["dg", "digi", "aadhaar"]):
        return "Sorry, this app cannot be opened."
    clean = app_name.replace("open", "").replace("kholo", "").strip()
    r = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    pkgs = [l.replace("package:", "").strip() for l in r.stdout.splitlines()]
    matches = [p for p in pkgs if clean in p.lower()]
    if not matches:
        sp = {"whatsapp": "com.whatsapp", "camera": "com.android.camera", "chrome": "com.android.chrome", "youtube": "com.google.android.youtube", "instagram": "com.instagram.android", "facebook": "com.facebook.katana", "chatgpt": "com.openai.chatgpt", "chat gpt": "com.openai.chatgpt", "gpt": "com.openai.chatgpt", "play store": "com.android.vending", "maps": "com.google.android.apps.maps", "map": "com.google.android.apps.maps", "calendar": "com.google.android.calendar", "album": "com.google.android.apps.photos", "gallery": "com.google.android.apps.photos", "fampay": "com.fampay.in", "hotstar": "in.startv.hotstar", "jio hotstar": "in.startv.hotstar", "castle": "com.castle.app", "call": "com.google.android.dialer", "phone": "com.google.android.dialer"}
        for k, v in sp.items():
            if k in clean: matches = [v]; break
    if not matches:
        return f"Sorry, {clean} is not installed."
    pkg = matches[0]
    act = subprocess.run(["cmd", "package", "resolve-activity", "--brief", pkg], capture_output=True, text=True)
    lines = act.stdout.strip().split("\n")
    if len(lines) > 1:
        component = lines[-1].strip()
        res = subprocess.run(["am", "start", "-n", component], capture_output=True)
        if res.returncode == 0: return f"Opening {clean} boss!"
    cmd_str = f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"
    res2 = subprocess.run(cmd_str, shell=True, capture_output=True)
    if res2.returncode == 0: return f"Opening {clean} boss!"
    return f"Sorry, could not open {clean}."

def gf_reply(q):
    if "love you" in q or "love u" in q: 
        return "I love you too jaan! Tum meri jaan ho."
    if "miss you" in q or "miss u" in q: 
        return "I missed you so much! Tum kahan the?"
    if "kiss" in q: 
        return "Muah! Main tumse bahut pyar karti hoon."
    if "kemon acho" in q or "kaise ho" in q: 
        return "Main theek hoon jaan. Tumhara din kaisa gaya? Kuch batao na."
    if "good morning" in q: 
        return "Good morning jaan! Aaj raat theek se soyi?"
    if "good night" in q: 
        return "Good night my love. Sweet dreams. Kal baat karenge."
    if "hello" in q or "hi" in q: 
        return "Hello baby! I missed you. Tum kya kar rahe ho?"
    if "tumi ki korcho" in q or "what are you doing" in q: 
        return "Main tumhara hi soch rahi hoon. Tum kaise ho?"
    return "Achha bolo jaan, tumhe kya achha lagta hai? Main sunna chahti hoon."

n = rec("nick") or "boss"
bolo(f"Welcome back {n}!", "en")

gf_mode = False

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)

    if any(x in q for x in ["girlfriend mode on", "gf mode on", "gf mood on", "girlfriend mood on", "love mode on"]):
        gf_mode = True
        bolo("Girlfriend mode on. I love you baby!")
        continue
        
    if any(x in q for x in ["girlfriend mode off", "gf mode off", "normal mode", "gf mood off"]):
        gf_mode = False
        bolo("Ok, back to normal boss.")
        continue

    if any(x in q for x in ["bye", "stop", "band"]):
        if gf_mode: bolo("Bye baby, talk to you soon!")
        else: bolo("Bye boss!")
        break

    if "good night" in q:
        if gf_mode: bolo("Good night my love. Sweet dreams.")
        else: bolo("Good night boss!")
        break

    if gf_mode:
        res = gf_reply(q)
        print("Mini:", res)
        bolo(res, "hi") 
        continue

    res = open_app_by_name(q)
    if res:
        print("Mini:", res)
        bolo(res, "en")
        continue

    if "hello" in q or "hi" in q: bolo(f"Hello {n}! Kaise ho?", "hi")
    elif "kaise" in q: bolo("Main theek hoon!", "hi")
    else: bolo("Sorry, I did not understand.", "en")
