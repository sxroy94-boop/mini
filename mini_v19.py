import os, subprocess, datetime, json, urllib.parse, urllib.request

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

def is_personal(q):
    words = ["my ", "my", "password", "pass", "amar", "amr", "name", "naam", "memory", "memo", "personal", "private", "address", "phone", "number", "email", "bank", "account", "aadhaar", "pan", "upi", "balance", "salary", "family", "wife", "husband", "girlfriend", "boyfriend", "boss"]
    for w in words:
        if w in q:
            return True
    return False

def open_web_search(q):
    query = q
    for kw in ["search for", "search", "google", "what is", "who is", "kya hai", "kaun hai", "tell me about", "number one", "richest", "capital", "history", "info"]:
        if kw in q:
            query = q.split(kw)[-1].strip()
            break
    query = query.replace("koro", "").replace("kar do", "").replace("do", "").replace("kro", "").strip()
    if not query:
        return None
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url], capture_output=True)
    return f"Opening Google search for {query} boss!"

def ask_wiki(q):
    query = q
    for kw in ["who is", "what is", "search for", "search", "google", "kya hai", "kaun hai", "tell me about", "number one", "richest", "capital"]:
        if kw in q:
            query = q.split(kw)[-1].strip()
            break
    query = query.replace("koro", "").replace("kar do", "").replace("do", "").replace("kro", "").strip()
    if not query:
        return None
    try:
        url = "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query) + "&format=json&no_html=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("AbstractText"):
                return data["AbstractText"]
            if data.get("Answer"):
                return data["Answer"]
    except:
        pass
    return None

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
        return None # Return None so it tries web search next
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

n = rec("nick") or "boss"
bolo(f"Welcome back {n}!", "en")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)

    if any(x in q for x in ["bye", "stop", "band"]):
        bolo("Bye boss!")
        break
    if "good night" in q:
        bolo("Good night boss!")
        break

    if is_personal(q):
        bolo("Sorry, I cannot share personal info.", "en")
        continue

    # Check if it's an app opening command
    if "open " in q or "kholo" in q:
        res = open_app_by_name(q)
        if res:
            print("Mini:", res)
            bolo(res, "en")
            continue

    # Check if it's a search/question command
    if any(x in q for x in ["search", "google", "who is", "what is", "kya hai", "kaun hai", "tell me about", "number one", "richest"]):
        res = ask_wiki(q)
        if res:
            print("Mini:", res)
            bolo(res, "en")
        else:
            res = open_web_search(q)
            if res:
                print("Mini:", res)
                bolo(res, "en")
            else:
                bolo("Sorry, I don't know the answer.", "en")
        continue

    # Default fallback for any other query
    res = open_app_by_name(q)
    if res:
        print("Mini:", res)
        bolo(res, "en")
        continue

    if "hello" in q or "hi" in q: bolo(f"Hello {n}! Kaise ho?", "hi")
    elif "kaise" in q: bolo("Main theek hoon!", "hi")
    else: bolo("Sorry, I did not understand.", "en")
