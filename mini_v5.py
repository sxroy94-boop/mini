import os
import subprocess
import datetime
import json
import hashlib

def bolo(t, b="hi"):
    os.system(f"termux-tts-speak -l {b} \"{t}\"")

def shono():
    print("Bolo...")
    r = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=15)
    t = r.stdout.strip().lower()
    if not t or "error" in t:
        return ""
    return t

MEM_FILE = "mini_memory.json"
PASS_FILE = "mini_pass.json"

def load_mem():
    try:
        with open(MEM_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_mem(m):
    with open(MEM_FILE, "w") as f:
        json.dump(m, f)

def remember(key, value):
    m = load_mem()
    m[key] = {"value": value, "time": datetime.datetime.now().isoformat()}
    save_mem(m)

def recall(key):
    m = load_mem()
    if key in m:
        return m[key]["value"]
    return None

def cleanup_mem():
    m = load_mem()
    now = datetime.datetime.now()
    new_m = {}
    for k, v in m.items():
        old = datetime.datetime.fromisoformat(v["time"])
        if (now - old).days < 35:
            new_m[k] = v
    save_mem(new_m)

def enc(t):
    return hashlib.sha256(t.encode()).hexdigest()[:16]

def load_pass():
    try:
        with open(PASS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_pass(p):
    with open(PASS_FILE, "w") as f:
        json.dump(p, f)

def memory_check(q):
    if "my name is" in q:
        name = q.split("my name is")[-1].strip()
        remember("name", name)
        return f"Ok, I will remember. Your name is {name}."
    if "call me" in q:
        nick = q.split("call me")[-1].strip()
        remember("nickname", nick)
        return f"Ok, I will call you {nick}."
    if "i am boss" in q:
        remember("nickname", "boss")
        return "Ok boss! Ab main aapko boss bulaungi."
    if "what is my name" in q:
        name = recall("name")
        if name:
            return f"Your name is {name}."
        return "Sorry, ami tomar naam jani na."
    if "my password is" in q:
        pwd = q.split("my password is")[-1].strip()
        p = load_pass()
        p["main"] = enc(pwd)
        save_pass(p)
        return "Ok, maine password yaad kar liya. Safely stored."
    if "what is my password" in q:
        return "Sorry, main password bol nahi sakti. Security ke liye."
    if "forget everything" in q:
        save_mem({})
        save_pass({})
        return "Ok, I forgot everything."
    return None

def buddhi(q):
    nick = recall("nickname") or recall("name") or "boss"
    if "hello" in q or "hi" in q or "hey" in q:
        return f"Hello {nick}! Kaise ho?", "hi"
    if "kaise" in q: return "Main theek hoon!", "hi"
    if "your name" in q: return "My name is mini.", "en"
    if "thank" in q: return "You are welcome!", "en"
    return "Sorry, I did not understand.", "en"

def greeting_reply(q):
    if "morning" in q: return "Good morning! Kaise ho?", "hi"
    if "afternoon" in q: return "Good afternoon!", "hi"
    if "evening" in q: return "Good evening!", "hi"
    if "night" in q: return "Good night! Sweet dreams.", "en"
    return None

cleanup_mem()
nick = recall("nickname") or recall("name")
if nick:
    bolo(f"Welcome back {nick}!", "en")
else:
    bolo("Hello! I am mini. Tumhara naam kya hai?", "hi")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "bye" in q or "by" in q or "stop" in q or "band" in q:
        bolo("Bye!", "en")
        break
    mem = memory_check(q)
    if mem:
        print("Mini:", mem)
        bolo(mem, "en")
        continue
    gr = greeting_reply(q)
    if gr:
        a, b = gr
    else:
        a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)