import os

def mini_bolo(text, bhasha="bn"):
    os.system(f'termux-tts-speak -l {bhasha} "{text}"')

print("mini চালু হয়েছে...")
mini_bolo("হ্যালো, আমি মিনি। আমি তোমার সহকারী।")
