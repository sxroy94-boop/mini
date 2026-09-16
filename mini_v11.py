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

def get_apps():
    r = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    return r.stdout.splitlines()

def open_app_by_name(app_name):
    app_name = app_name.lower().strip()
    if "dg" in app_name or "digi" in app_name or "aadhaar" in app_name:
        return "Sorry, this app cannot be opened."
    apps = get_apps()
    matches = []
    for a in apps:
        if app_name in a.lower():
            matches.append(a.replace("package:", ""))
    if len(matches) == 1:
        pkg = matches[0]
        subprocess.run(["monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
        return "Opening " + app_name + " boss!"
    elif len(matches) > 1:
        return "Multiple apps found for " + app_name + "."
    else:
        return "Sorry, " + app_name + " is not installed."

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
    if "morning" in q:
        bolo("Good morning boss! Kaise ho aap?", "hi")
        continue
    if "afternoon" in q:
        bolo("Good afternoon boss! Aapka din kaisa giya hai?", "hi")
        continue
    if "evening" in q:
        bolo("Good evening boss! Aaj ka din kaisa tha?", "hi")
        continue
    mc = mem_check(q)
    if mc:
        print("Mini:", mc)
        bolo(mc, "en")
        continue
    if "hello" in q or "hi" in q:
        bolo("Hello " + n + "! Kaise ho?", "hi")
    elif "kaise" in q:
        bolo("Main theek hoon!", "hi")
    else:
        bolo("Sorry, I did not understand.", "en")