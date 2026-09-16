import os
import datetime
import json
import urllib.parse
import urllib.request
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

# ESP32 IP Address (Pore ESP32 asle ei IP change korba)
ESP32_IP = "192.168.1.100"

def send_to_esp32(command):
    """ESP32 te command pathabe (pore use hobe)"""
    print(f"ESP32 COMMAND: {command}")
    # Pore ei line ta uncomment korba:
    # url = f"http://{ESP32_IP}/{command}"
    # try: urllib.request.urlopen(url, timeout=3)
    # except: pass

class MiniApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        self.label = Label(text="Hello Boss! I am mini.\nPress the button to start.", font_size='20sp')
        btn = Button(text="Start mini", size_hint=(1, 0.3))
        btn.bind(on_press=self.start_mini)
        layout.add_widget(self.label)
        layout.add_widget(btn)
        return layout

    def start_mini(self, instance):
        self.label.text = "mini is running...\n(ESP32 connection ready)"
        send_to_esp32("BOOT")

if __name__ == "__main__":
    MiniApp().run()
