import os
import subprocess
import datetime
import json

def bolo(t, b="en"):
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

def open_app_by_name(app_name):
    app_name = app_name.lower().strip()
    if "dg" in app_name or "digi" in app_name or "aadhaar" in app_name:
        return "Sorry, this app cannot be opened."
    search_name = app_name.replace(" ", "")
    r = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    matches = []
    for line in r.stdout.splitlines():
        pkg = line.replace("package:", "").strip()
        if search_name in pkg.lower():
            matches.append(pkg)
    if not matches:
        for line in r.stdout.splitlines():
            pkg = line.replace("package:", "").strip()
            if app_name in pkg.lower():
                matches.append(pkg)
    if not matches:
        return "Sorry, " + app_name + " is not installed."
    pkg = matches[0]
    if app_name == "camera":
        for p in matches:
            if "camera" in p and "provider" not in p:
                pkg = p
                break
    elif app_name == "whatsapp":
        for p in matches:
            if p == "com.whatsapp":
                pkg = p
                break
    elif app_name in ["chatgpt", "chat gpt", "gpt"]:
        for p in matches:
            if p == "com.openai.chatgpt":
                pkg = p
                break
    res = subprocess.run(["monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
    if res.returncode == 0:
        return "Opening " + app_name + " boss!"
    else:
        act = subprocess.run(["cmd", "package", "resolve-activity", "--brief", pkg], capture_output=True, text=True)
        lines = act.stdout.strip().split("\n")
        if len(lines) > 1:
            component = lines[-1].strip()
            res2 = subprocess.run(["am", "start", "-n", component], capture_output=True)
            if res2.returncode == 0:
                return "Opening " + app_name + " boss!"
        return "Sorry, could not open " + app_name + "."

def find_number(name):
    try:
        r = subprocess.run(["termux-contact-list"], capture_output=True, text=True, timeout=8)
        contacts = json.loads(r.stdout)
    except:
        contacts = []
    for c in contacts:
        if name in c.get("name", "").lower():
            return c.get("number", "")
    return None

def make_call(q):
    if "call" not in q:
        return None
    target = q.replace("call", "").replace("karo", "").replace("kro", "").replace("kar do", "").strip()
    if not target:
        return None
    num = find_number(target)
    if num:
        subprocess.run(["termux-telephony-call", num], capture_output=True)
        return "Calling " + target + " boss!"
    return "Contact " + target + " not found."

n = rec("nick") or "boss"
h = datetime.datetime.now().hour
if 12 <= h < 17:
    bolo("Good afternoon " + n + "! Aapka din kaisa giya hai?", "hi")
elif 17 <= h <= 22:
    bolo("Good evening " + n + "! Aaj ka din kaisa tha?", "hi")
else:
    bolo("Welcome back " + n + "!", "en")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "good night" in q:
        bolo("Good night boss!", "en")
        break
    if "bye" in q or "stop" in q or "band" in q:
        bolo("Bye boss!", "en")
        break
    if "open " in q:
        app = q.split("open")[-1].strip()
        res = open_app_by_name(app)
        print("Mini:", res)
        bolo(res, "en")
        continue
    if "kholo" in q:
        app = q.replace("kholo", "").strip()
        res = open_app_by_name(app)
        print("Mini:", res)
        bolo(res, "en")
        continue
    res = make_call(q)
    if res:
        print("Mini:", res)
        bolo(res, "en")
        continue
    if "morning" in q:
        bolo("Good morning boss! Kaise ho aap?", "hi")
        continue
    if "afternoon" in q:
        bolo("Good afternoon boss! Aapka din kaisa giya hai?", "hi")
        continue
    if "evening" in q:
        bolo("Good evening boss! Aaj ka din kaisa tha?", "hi")
        continue
    if "hello" in q or "hi" in q:
        bolo("Hello " + n + "! Kaise ho?", "hi")
    elif "kaise" in q:
        bolo("Main theek hoon!", "hi")
    else:
        bolo("Sorry, I did not understand.", "en")