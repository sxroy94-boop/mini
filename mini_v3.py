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

def samay_bolo():
    h = datetime.datetime.now().hour
    if 6 <= h < 10: return "Good morning! Kaise ho aap?", "hi"
    if 12 <= h < 17: return "Good afternoon! Kya kar rahe ho?", "hi"
    if 17 <= h < 22: return "Good evening! Aaj ka din kaisa tha?", "hi"
    if h == 22: return "Din ho gaya hai. Aap dinner kar lijiye.", "hi"
    return "Good night! Sweet dreams.", "en"

def greeting_reply(q):
    if "morning" in q: return "Good morning! Kaise ho aap?", "hi"
    if "afternoon" in q: return "Good afternoon! Kya haal hai?", "hi"
    if "evening" in q: return "Good evening! Aaj kaisa din tha?", "hi"
    if "night" in q: return "Good night! Sweet dreams.", "en"
    return None

def buddhi(q):
    if "hello" in q or "hi" in q or "hey" in q: return "Hello! I am mini. Aap kaise ho?", "hi"
    if "kaise" in q or "kaisi" in q: return "Main theek hoon! Aap kaise ho?", "hi"
    if "how are you" in q: return "I am fine! How are you?", "en"
    if "your name" in q: return "My name is mini. Aap kaun ho?", "hi"
    if "nam" in q or "naam" in q: return "Mera naam mini hai. Aapka naam kya hai?", "hi"
    if "time" in q:
        n = datetime.datetime.now().strftime("%I:%M %p")
        return f"Time is {n}. Aur batao?", "en"
    if "thank" in q: return "You are welcome! Aur batao?", "en"
    if "namaste" in q: return "Namaste! Main mini hoon. Aap kaise ho?", "hi"
    return "Sorry, I did not understand.", "en"

s, sb = samay_bolo()
bolo(s, sb)
while True:
    q = shono()
    if not q: continue
    print("Tumi:", q)
    if "bye" in q or "by" in q or "stop" in q or "band" in q:
        bolo("Bye! See you again.", "en")
        break
    gr = greeting_reply(q)
    if gr:
        a, b = gr
    else:
        a, b = buddhi(q)
    print("Mini:", a)
    bolo(a, b)