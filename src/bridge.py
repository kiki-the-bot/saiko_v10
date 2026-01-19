import queue
import threading
import asyncio
import logging

# Config
from config.settings import AgentConfig

# Components
from src.core.cortex import NeuroCortex
from src.core.parser import ChaosParser
from src.core.controller import SaikoController, CallSession

# External Dependencies (Assumed in root)
from src.core.engine import SaikoEngine
#from src.audio.mouth import Mouth

logger = logging.getLogger("SaikoSystem")

class BrainBridge:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.cfg = AgentConfig()
        
        # Init Components
        self.cortex = NeuroCortex(self.cfg)
        self.llm = SaikoEngine(self.cfg, self.cfg.MODEL_PATH)
        self.parser = ChaosParser()
        self.controller = SaikoController(self.cortex, self.llm, self.parser)
        
        # Init Session
        self.current_session = CallSession()
        
        #self.mouth = Mouth()
        self.running = True
        threading.Thread(target=self._run_loop, daemon=True).start()
        logger.info("✅ Bridge Online.")

    def reset_call(self):
        if self.current_session:
            self.current_session.abort_signal = True
        self.current_session = CallSession()
        self.parser = ChaosParser()
        logger.info("MEMORY WIPE ")

    def send_chat_msg(self, msg_object):
        self.input_queue.put(msg_object)

    def trigger_interrupt(self):
        logger.warning("🛑 INTERRUPT TRIGGERED")
        self.current_session.abort_signal = True

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def queue_watcher():
            while self.running:
                try:
                    # Run blocking queue.get in executor
                    msg = await loop.run_in_executor(None, self.input_queue.get)
                    if msg is None: break

                    async def stream_callback(token):
                        self.output_queue.put(("TOKEN", token))
                    
                    result = await self.controller.process_turn(self.current_session, msg, stream_callback)

                    if result:                    
                        self.output_queue.put(("FINAL", result))

                        if hasattr(msg, 'reply_q') and msg.reply_q is not None:
                            print(f"sending message to API")
                            msg.reply_q.put(result)
                except Exception as e:
                    logger.error(f"FATAL CRASH: {e}", exc_info=True)
        
        loop.run_until_complete(queue_watcher())

    def get_updates(self):
        updates = []
        try:
            while True:
                updates.append(self.output_queue.get_nowait())
        except queue.Empty: pass
        return updates