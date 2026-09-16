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

MEM_FILE = "mini_memory.json"

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

def samay_bolo():
    h = datetime.datetime.now().hour
    if 6 <= h < 10: return "Good morning!", "en"
    if 12 <= h < 17: return "Good afternoon!", "en"
    if 17 <= h < 22: return "Good evening!", "en"
    return "Good night!", "en"

def memory_check(q):
    if "my name is" in q:
        name = q.split("my name is")[-1].strip()
        remember("name", name)
        return f"Ok, I will remember. Your name is {name}."
    if "mera naam" in q or "my naam" in q:
        parts = q.split("naam")
        if len(parts) > 1:
            name = parts[-1].replace("is", "").strip()
            remember("name", name)
            return f"Ok, aapka naam {name} hai. Main yaad rakhungi."
    if "what is my name" in q or "mera naam kya" in q or "amar nam ki" in q:
        name = recall("name")
        if name:
            return f"Your name is {name}."
        return "Sorry, ami tomar naam jani na."
    if "forget everything" in q or "delete memory" in q:
        save_mem({})
        return "Ok, I forgot everything."
    return None

def buddhi(q):
    if "hello" in q or "hi" in q or "hey" in q:
        name = recall("name")
        if name:
            return f"Hello {name}! Kaise ho?", "hi"
        return "Hello! Aap kaun ho? Apna naam batao.", "hi"
    if "kaise" in q or "kaisi" in q: return "Main theek hoon!", "hi"
    if "how are you" in q: return "I am fine!", "en"
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
name = recall("name")
if name:
    bolo(f"Welcome back {name}!", "en")
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