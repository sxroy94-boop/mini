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
    if pkg:
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

def find_number(name):
    try:
        r = subprocess.run(["termux-contact-list"], capture_output=True, text=True, timeout=8)
        contacts = json.loads(r.stdout)
    except: contacts = []
    for c in contacts:
        if name in c.get("name", "").lower(): return c.get("number", "")
    return None

def make_call(q):
    if "call" not in q: return None
    target = q.replace("call", "").replace("karo", "").replace("kro", "").replace("kar do", "").strip()
    if not target: return None
    num = find_number(target)
    if num:
        subprocess.run(["termux-telephony-call", num], capture_output=True)
        return f"Calling {target} boss!"
    return f"Contact {target} not found."

def wa_call(q):
    if "whatsapp" not in q or not any(x in q for x in ["call", "message", "msg"]): return None
    words = q.split(); name = None
    for w in words:
        if w not in ["whatsapp", "call", "karo", "kro", "message", "msg", "me", "ko", "to", "pe", "par"]:
            name = w
    if name:
        num = find_number(name)
        if num:
            clean_num = num.replace("+", "").replace(" ", "").replace("-", "")
            if len(clean_num) == 10: clean_num = "91" + clean_num
            url = f"https://wa.me/{clean_num}"
            if subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True).returncode == 0:
                return f"Opening WhatsApp chat with {name} boss!"
        return f"Contact {name} not found."
    return None

def navigate(q):
    place = None
    for kw in ["navigate to", "go to", "take me to", "raasta batao", "kahan jaana"]:
        if kw in q: place = q.split(kw)[-1].strip(); break
    if place:
        url = "google.navigation:q=" + place.replace(" ", "+")
        if subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True).returncode == 0:
            return f"Navigating to {place} boss!"
        return "Maps open nahi hua."
    return None

def play_search(q):
    if "play store" in q and any(x in q for x in ["search", "dhundo", "download"]):
        app = q.split("search")[-1] if "search" in q else q.split("download")[-1]
        app = app.replace("play store", "").replace("on", "").strip()
        if app:
            url = "market://search?q=" + app.replace(" ", "+")
            if subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True).returncode == 0:
                return f"Searching {app} on Play Store boss!"
    return None

def mem_check(q):
    if "call me" in q:
        n = q.split("call me")[-1].strip(); rem("nick", n); return f"Ok, I will call you {n}"
    if "my password is" in q:
        pw = q.split("my password is")[-1].strip(); rem("pwd", pw); return "Password saved."
    if "what is my password" in q:
        pw = rec("pwd")
        if pw: return f"Your password is {pw}"
        return "No password saved."
    return None

n = rec("nick") or "boss"
h = datetime.datetime.now().hour
if 12 <= h < 17: bolo(f"Good afternoon {n}! Aapka din kaisa giya hai?", "hi")
elif 17 <= h <= 22: bolo(f"Good evening {n}! Aaj ka din kaisa tha?", "hi")
else: bolo(f"Welcome back {n}!", "en")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "good night" in q: bolo("Good night boss!", "en"); break
    if any(x in q for x in ["bye", "stop", "band"]): bolo("Bye boss!", "en"); break
    res = wa_call(q) or navigate(q) or play_search(q) or make_call(q) or open_app_by_name(q)
    if res:
        print("Mini:", res); bolo(res, "en"); continue
    if "morning" in q: bolo("Good morning boss! Kaise ho aap?", "hi"); continue
    if "afternoon" in q: bolo("Good afternoon boss! Aapka din kaisa giya hai?", "hi"); continue
    if "evening" in q: bolo("Good evening boss! Aaj ka din kaisa tha?", "hi"); continue
    mc = mem_check(q)
    if mc: print("Mini:", mc); bolo(mc, "en"); continue
    if "hello" in q or "hi" in q: bolo(f"Hello {n}! Kaise ho?", "hi")
    elif "kaise" in q: bolo("Main theek hoon!", "hi")
    else: bolo("Sorry, I did not understand.", "en")
