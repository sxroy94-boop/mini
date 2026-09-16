import os
import subprocess
import datetime

def bolo(t, b="hi"):
    os.system(f"termux-tts-speak -l {b} \"{t}\"")

def shono():
    print("Bolo...")
    r = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=15)
    t = r.stdout.strip().lower()
    if not t or "error" in t:
        return ""
    return t

def buddhi(q):
    if "hello" in q: return "Hello! I am mini.", "en"
    if "kaise" in q: return "Main theek hoon!", "hi"
    if "kemon" in q: return "Ami bhalo achi!", "bn"
    if "nam" in q: return "Mera naam mini hai.", "hi"
    if "bye" in q: return "Bye!", "en"
    return "Sorry, bujhi ni.", "bn"

bolo("Hi ami mini", "bn")
while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "bye" in q:
        bolo("Bye", "en")
        break
    a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)