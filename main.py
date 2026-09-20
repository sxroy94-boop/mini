from kivy.app import App
from kivy.uix.label import Label

class MiniApp(App):
    def build(self):
        return Label(text="Hello Boss! I am mini.")

if __name__ == "__main__":
    MiniApp().run()
