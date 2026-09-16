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

def mem_check(q):
    if "call me" in q:
        n = q.split("call me")[-1].strip()
        rem("nick", n)
        return "Ok, I will call you " + n
    if "my password is" in q:
        pw = q.split("my password is")[-1].strip()
        rem("pwd", pw)
        return "Password saved."
    if "what is my password" in q or "mera password" in q:
        pw = rec("pwd")
        if pw: return "Your password is " + pw
        return "No password saved."
    if "forget everything" in q:
        sm({})
        return "Everything forgotten."
    return None

def buddhi(q):
    n = rec("nick") or "boss"
    if "hello" in q or "hi" in q or "hey" in q:
        return "Hello " + n + "! Kaise ho?", "hi"
    if "kaise" in q: return "Main theek hoon!", "hi"
    if "your name" in q: return "My name is mini.", "en"
    if "thank" in q: return "You are welcome!", "en"
    return "Sorry, I did not understand.", "en"

def greeting_reply(q):
    if "morning" in q: return "Good morning!", "en"
    if "afternoon" in q: return "Good afternoon!", "en"
    if "evening" in q: return "Good evening!", "en"
    if "night" in q: return "Good night!", "en"
    return None

n = rec("nick")
if n:
    bolo("Welcome back " + n + "!", "en")
else:
    bolo("Hello! I am mini.", "en")

while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "bye" in q or "by" in q or "stop" in q or "band" in q:
        bolo("Bye!", "en")
        break
    mc = mem_check(q)
    if mc:
        print("Mini:", mc)
        bolo(mc, "en")
        continue
    gr = greeting_reply(q)
    if gr:
        a, b = gr
    else:
        a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)