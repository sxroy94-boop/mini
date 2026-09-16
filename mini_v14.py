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

def gf_buddhi(q):
    if "love you" in q: return "I love you too baby!"
    if "miss you" in q: return "I missed you so much! Where were you?"
    if "kiss" in q: return "Muah!"
    if "good night" in q: return "Good night my love. Sweet dreams."
    if "good morning" in q: return "Good morning jaan! Did you sleep well?"
    if "kemon acho" in q or "kaise ho" in q: return "Tomake dekhe bhalo lagche jaan! Kaise ho tum?"
    if "hello" in q or "hi" in q: return "Hello baby! Ami tomake miss korchilam."
    if "sensitive" in q or "intimate" in q: return "Tumi amar sob kichu. Ami shob bujhi."
    return "Ami tomake bhalobashi. Tumi ki korcho?"

n = rec("nick") or "boss"
h = datetime.datetime.now().hour
if 12 <= h < 17: bolo(f"Good afternoon {n}!", "hi")
elif 17 <= h <= 22: bolo(f"Good evening {n}!", "hi")
else: bolo(f"Welcome back {n}!", "en")

gf_mode = False

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)

    if ("girlfriend mode on" in q or "girlfriend mood on" in q or "gf mode on" in q or "gf mood on" in q or "love mode on" in q or "girlfriend on" in q or "gf on" in q):
        gf_mode = True
        bolo("Girlfriend mode on. I love you baby!")
        continue
    if "girlfriend mode off" in q or "gf mode off" in q or "normal mode" in q:
        gf_mode = False
        bolo("Ok, back to normal boss.")
        continue

    if any(x in q for x in ["bye", "stop", "band"]):
        bolo("Bye baby, talk to you soon!" if gf_mode else "Bye boss!")
        break

    if "good night" in q:
        if gf_mode: bolo("Good night my love.")
        else: bolo("Good night boss!")
        break

    res = open_app_by_name(q)
    if res:
        print("Mini:", res)
        bolo(res, "en")
        continue

    if gf_mode:
        res = gf_buddhi(q)
        print("Mini:", res)
        bolo(res, "en" if "love" in res or "Hello" in res or "Muah" in res or "Good" in res else "hi")
    else:
        if "hello" in q or "hi" in q: bolo(f"Hello {n}! Kaise ho?", "hi")
        elif "kaise" in q: bolo("Main theek hoon!", "hi")
        else: bolo("Sorry, I did not understand.", "en")
