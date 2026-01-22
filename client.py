import asyncio
import aiohttp
import logging
import colorama
from colorama import Fore, Style
from datetime import datetime

# ✅ USE YOUR EXISTING MODULES
from src.audio.faster_ears import SaikoEars
from src.audio.mouth import Mouth

# --- CONFIG ---
API_URL = "http://localhost:8000/chat"
NAME = "SAIKO"

logging.basicConfig(level=logging.ERROR)
colorama.init(autoreset=True)

class AsyncSaikoClient:
    def __init__(self):
        print(Fore.GREEN + "🔌 INITIALIZING NEURAL LINK (ASYNC/OFFLINE)...")
        
        # 1. Init Mouth (It handles its own threading, so it's safe!)
        self.mouth = Mouth()
        
        # 2. Get Event Loop
        self.loop = asyncio.get_event_loop()
        
        # 3. Init Ears
        self.ears = SaikoEars(callback_function=self.bridge_callback)
        
        print(Fore.CYAN + "✅ BODY ONLINE.")

    def bridge_callback(self, text, lang="en"):
        """Teleports audio text from Ears thread to Main Async Loop"""
        asyncio.run_coroutine_threadsafe(self.process_input(text), self.loop)

    async def process_input(self, user_text):
        print(f"\n{Fore.BLUE}[YOU]: {user_text}")

        try:
            t0 = datetime.now()
            # Non-blocking HTTP call
            async with aiohttp.ClientSession() as session:
                payload = {"role": "user", "prompt": user_text}
                async with session.post(API_URL, json=payload) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        latency = (datetime.now() - t0).total_seconds()
                        self.handle_response(data, latency)
                    else:
                        print(Fore.RED + f"❌ API ERROR: {response.status}")
                        
        except Exception as e:
            print(Fore.RED + f"❌ CONNECTION FAILED: {e}")

    def handle_response(self, data, latency):
        reply = data.get("response", "")
        status = data.get("status", "")
        scenario = data.get("scenario", "UNKNOWN")

        # 🛑 UI FEEDBACK FOR HUNTING
        if status == "hunting":
            print(Fore.YELLOW + f"👀 [HUNTING] ({latency:.2f}s) - Waiting for full order ID...")
            return

        # 🗣️ SPEAK
        if reply:
            print(f"{Fore.GREEN}[{NAME} - {scenario}]: {reply} {Style.DIM}({latency:.2f}s)")
            
            # ✅ JUST CALL IT. Your mouth.py is already threaded!
            self.mouth.say(reply)

    async def run(self):
        self.ears.start_listening()
        print(Fore.MAGENTA + "✨ SYSTEM READY. SPEAK NOW.")
        
        try:
            # Infinite sleep to keep the script running
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            print(Fore.RED + "\n🔌 SHUTTING DOWN.")
            self.ears.shutdown()

if __name__ == "__main__":
    client = AsyncSaikoClient()
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        pass