import pyttsx3
import threading

class Mouth:
    def __init__(self):
        self.engine = pyttsx3.init()
        
        # TWEAK THE VOICE (Optional)
        voices = self.engine.getProperty('voices')
        # On Windows, voices[1] is usually female (Zira). voices[0] is male (David).
        try:
            self.engine.setProperty('voice', voices[1].id) 
        except:
            pass
            
        self.engine.setProperty('rate', 175) # Speed (Default is 200, slow it down a bit)
        self.engine.setProperty('volume', 1.0)

    def say(self, text):
        # We run this in a thread so it doesn't block the brain while speaking
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def _speak_thread(self, text):
        try:
            # Clean up text (remove [THOUGHT] blocks just in case)
            if "[THOUGHT]" in text: return 
            
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass