import pyttsx3
import threading

class Mouth:
    def __init__(self):
        self.engine = pyttsx3.init()
        
        voices = self.engine.getProperty('voices')

        try:
            self.engine.setProperty('voice', voices[1].id) 
        except:
            pass
            
        self.engine.setProperty('rate', 175)
        self.engine.setProperty('volume', 1.0)

    def say(self, text):

        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        try:
            if "[THOUGHT]" in text: return 
            
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass