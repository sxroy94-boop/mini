import os, subprocess, datetime, json, urllib.parse, urllib.request, re

def bolo(t, b="en"):
    os.system(f'termux-tts-speak -l {b} "{t}"')

def shono():
    print("Bolo...")
    r = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=15)
    t = r.stdout.strip().lower()
    return t if t and "error" not in t else ""

MEM = "mini_mem.json"
PWD = "mini_pwd.json"

def lm():
    try:
        with open(MEM) as f: return json.load(f)
    except: return {}
def sm(m):
    with open(MEM, "w") as f: json.dump(m, f)
def lp():
    try:
        with open(PWD) as f: return json.load(f)
    except: return {}
def sp(p):
    with open(PWD, "w") as f: json.dump(p, f)
def rec(k):
    m = lm(); return m[k]["v"] if k in m else None
def rem(k, v):
    m = lm(); m[k] = {"v": v, "t": datetime.datetime.now().isoformat()}; sm(m)

def is_personal_query(q):
    words = ["my password", "mera password", "amar password", "password kya", "password ki", "password bolo", "show password", "password jante", "what is my password"]
    for w in words:
        if w in q: return True
    return False

def extract_password(q):
    clean = q.replace("save", "").replace("my", "").replace("mera", "").replace("amar", "").replace("password", "").replace("is", "").replace("koro", "").replace("kro", "").strip()
    if clean: return clean
    return None

def web_search_read(q):
    query = q
    for kw in ["search for", "search", "google", "who is", "what is", "kya hai", "kaun hai", "tell me about", "number one", "richest", "capital", "history", "info", "movie"]:
        if kw in q:
            query = q.split(kw)[-1].strip(); break
    query = query.replace("koro", "").replace("kar do", "").replace("do", "").replace("kro", "").strip()
    if not query: return None
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode()
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            if snippets:
                return re.sub(r'<[^>]+>', '', snippets[0]).strip()
    except: pass
    return None

def open_web_search(q):
    query = q
    for kw in ["search for", "search", "google", "who is", "what is", "kya hai", "kaun hai", "tell me about", "number one", "richest", "capital", "history", "info", "movie"]:
        if kw in q:
            query = q.split(kw)[-1].strip(); break
    query = query.replace("koro", "").replace("kar do", "").replace("do", "").replace("kro", "").strip()
    if not query: return None
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True)
    return f"Opening Google search for {query} boss!"

def open_app_by_name(app_name):
    app_name = app_name.lower().strip()
    if any(x in app_name for x in ["dg", "digi", "aadhaar"]):
        return "Sorry, this app cannot be opened."
    clean = app_name.replace("open", "").replace("kholo", "").strip()
    r = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    pkgs = [l.replace("package:", "").strip() for l in r.stdout.splitlines()]
    matches = [p for p in pkgs if clean in p.lower()]
    if not matches:
        sp_ = {"whatsapp": "com.whatsapp", "camera": "com.android.camera", "chrome": "com.android.chrome", "youtube": "com.google.android.youtube", "instagram": "com.instagram.android", "facebook": "com.facebook.katana", "chatgpt": "com.openai.chatgpt", "chat gpt": "com.openai.chatgpt", "gpt": "com.openai.chatgpt", "play store": "com.android.vending", "maps": "com.google.android.apps.maps", "map": "com.google.android.apps.maps", "calendar": "com.google.android.calendar", "album": "com.google.android.apps.photos", "gallery": "com.google.android.apps.photos", "fampay": "com.fampay.in", "hotstar": "in.startv.hotstar", "jio hotstar": "in.startv.hotstar", "castle": "com.castle.app", "call": "com.google.android.dialer", "phone": "com.google.android.dialer"}
        for k, v in sp_.items():
            if k in clean: matches = [v]; break
    if not matches: return None
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

def normal_reply(q, n):
    # Common phrases
    if any(x in q for x in ["thank", "thanks", "thx", "dhanyabad", "shukriya"]):
        return "You are welcome " + n + "!"
    if any(x in q for x in ["ok", "okay", "okey", "acha", "achha", "theek", "thik"]):
        return "Ok " + n + "!"
    if any(x in q for x in ["how are you", "kaise ho", "kaisi ho", "kemon acho"]):
        return "Main theek hoon! Aap kaise ho?"
    if any(x in q for x in ["your name", "tumhara naam", "what is your name"]):
        return "My name is mini."
    if any(x in q for x in ["good morning", "morning"]):
        return "Good morning " + n + "! Kaise ho aap?"
    if any(x in q for x in ["good afternoon", "afternoon"]):
        return "Good afternoon " + n + "! Aapka din kaisa giya hai?"
    if any(x in q for x in ["good evening", "evening"]):
        return "Good evening " + n + "! Aaj ka din kaisa tha?"
    if any(x in q for x in ["good night", "night"]):
        return "Good night " + n + "! Sweet dreams."
    if any(x in q for x in ["i love you", "love you", "pyar"]):
        return "I love you too " + n + "!"
    if any(x in q for x in ["sorry"]):
        return "No problem " + n + "!"
    if any(x in q for x in ["hello", "hi", "hey"]):
        return "Hello " + n + "! Kaise ho?"
    if any(x in q for x in ["bye", "goodbye"]):
        return "Bye " + n + "!"
    if any(x in q for x in ["help", "madad"]):
        return "Bolo " + n + ", main kya karu?"
    if any(x in q for x in ["yes", "haan", "ha", "yeah"]):
        return "Ok " + n + "!"
    if any(x in q for x in ["no", "nahi", "nope"]):
        return "Theek hai " + n + "."
    return None

n = rec("nick") or "boss"
bolo(f"Welcome back {n}!", "en")

personal_mode = False

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)

    if any(x in q for x in ["bye", "stop", "band"]):
        bolo("Bye baby!" if personal_mode else "Bye boss!")
        break

    if "password" in q and ("save" in q or "remember" in q or any(c.isdigit() for c in q)):
        pwd = extract_password(q)
        if pwd:
            p = lp(); p["main"] = pwd; sp(p)
            bolo("Password saved permanently boss.", "en")
        else:
            bolo("Please say the password clearly.", "en")
        continue

    if is_personal_query(q):
        p = lp()
        if "main" in p:
            bolo(f"Your password is {p['main']}", "en")
        else:
            bolo("No password saved.", "en")
        continue

    if "personal mood" in q or "personal mode" in q or "private mode" in q:
        personal_mode = True
        bolo("Personal mood on. Everything is private now.", "en")
        continue
    if "normal mood" in q or "normal mode" in q or "public mode" in q:
        personal_mode = False
        bolo("Normal mode on boss.", "en")
        continue

    if personal_mode:
        if any(x in q for x in ["hello", "hi"]):
            bolo(f"Hello jaan! Kaise ho?", "hi")
        elif "love" in q:
            bolo("I love you too jaan.", "hi")
        elif any(x in q for x in ["kaise", "kemon"]):
            bolo("Main theek hoon jaan.", "hi")
        elif any(x in q for x in ["thank", "thanks", "dhanyabad"]):
            bolo("Aww, koi baat nahi jaan!", "hi")
        elif "good night" in q:
            bolo("Good night my love. Sweet dreams.", "hi")
        else:
            bolo("Bolo jaan, main sun rahi hoon.", "hi")
        continue

    if any(x in q for x in ["search", "google", "who is", "what is", "kya hai", "kaun hai", "tell me about", "number one", "richest", "movie"]):
        res = web_search_read(q)
        if res:
            print("Mini:", res); bolo(res, "en")
        else:
            res = open_web_search(q)
            if res:
                print("Mini:", res); bolo(res, "en")
            else:
                bolo("Sorry, I don't know the answer.", "en")
        continue

    if "open " in q or "kholo" in q:
        res = open_app_by_name(q)
        if res:
            print("Mini:", res); bolo(res, "en")
            continue

    # Normal reply for common phrases
    rep = normal_reply(q, n)
    if rep:
        print("Mini:", rep)
        bolo(rep, "en")
        continue

    bolo("Sorry, I did not understand.", "en")
