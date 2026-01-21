import asyncio
import uuid
import logging
from typing import List
from dataclasses import dataclass, field
from textwrap import dedent

# Import Local Modules
# Adjust these imports if you moved ammo/mock_database!
from src.data.ammo import ChatMsg, ContextData
from src.data.database import OmniCorpDB

# Import our new separated cores
from src.core.cortex import NeuroCortex
from src.core.parser import ChaosParser
from src.core.engine import SaikoEngine # Assumes engine.py is in root or PYTHONPATH

logger = logging.getLogger("SaikoSystem")

@dataclass
class CallSession:
    """Holds the entire state of a single conversation."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state: str = "DISCOVERY"
    history: List[ChatMsg] = field(default_factory=list)
    context: ContextData = field(default_factory=ContextData)
    abort_signal: bool = False
    parser_buffer: str = ""

class SaikoController:
    """
    Stateless Logic Controller.
    Takes a Session + Analysis -> Updates Session + Returns Action.
    """
    def __init__(self, cortex: NeuroCortex, llm: SaikoEngine, parser: ChaosParser):
        self.cortex = cortex
        self.llm = llm
        self.parser = parser

    async def process_turn(self, session: CallSession, inbound_msg: ChatMsg, stream_callback):
        # 1. Update History
        session.history.append(inbound_msg)
        text = inbound_msg.content
        logger.info(f"🎮 Session {session.session_id} [{session.state}]: {text}")

        # 2. RUN CORTEX CASCADE (The New Priority System)
        analysis = self.cortex.analyze_input(text)
        logger.info(f"🧠 Cortex Analysis: {analysis}")

        # 3. HANDLE URGENT (Tier 1)
        if analysis['type'] == "URGENT":
            if analysis['label'] == "STOP":
                logger.warning("🛑 USER ORDERED STOP")
                session.abort_signal = True # Signal the generator to die
                return await self._fast_return("Stopping.", session.state, stream_callback)
            
            elif analysis['label'] == "ESCALATE":
                session.state = "EDUCATE"
                session.context.intent = "ESCALATION"
                logger.info("🚨 Escalate -> EDUCATE")
                # Fall through to routing to generate response
            
            elif analysis['label'] == "CORRECTION":
                session.state = "ORGANIZE"
                session.context.order_id = None
                return await self._fast_return("Apologies. Let's start over.", "ORGANIZE", stream_callback)

        # 4. HANDLE PASSIVE (Tier 2)
        elif analysis['type'] == "PASSIVE":
            resp = "Anything else?" if session.state == "REINFORCE" else "Go on."
            return await self._fast_return(resp, session.state, stream_callback)

        # 5. HANDLE INTENT (Tier 3)
        elif analysis['type'] == "INTENT":
            # If we are in Reinforce, a new intent means RE-OPEN CASE
            if session.state == "REINFORCE":
                logger.info(f"🔀 Re-opening case for {analysis['label']}")
                session.state = "EDUCATE"
                session.context.intent = analysis['label']
            else:
                session.context.intent = analysis['label']

        # 6. ROUTE BASED ON STATE
        if session.state == "DISCOVERY": 
            return await self._phase_discovery(session, text, analysis, stream_callback)
        elif session.state == "ORGANIZE": 
            return await self._phase_order(session, text, stream_callback)
        elif session.state == "EDUCATE": 
            return await self._phase_educate(session, text, stream_callback)
        elif session.state == "REINFORCE": 
            return await self._phase_reinforce(session, text, stream_callback)
        else:
            return await self._generate_llm_response(session, "GENERAL", text, stream_callback)

    # --- PHASES ---

    async def _phase_discovery(self, session: CallSession, text: str, analysis: dict, callback):
        # Check for Order ID (Parser)
        status, new_buf, data = self.parser.parse(text, session.parser_buffer)
        session.parser_buffer = new_buf
        
        if status == "LOCKED":
            session.context.order_id = data
            logger.info(f"✅ Order ID Found: {data}")

        # Decision Matrix
        if session.context.order_id and session.context.intent:
            return await self._fetch_and_educate(session, callback)
        
        elif session.context.order_id:
            session.context.intent = "STATUS"
            return await self._fetch_and_educate(session, callback)

        elif session.context.intent:
            session.state = "ORGANIZE"
            return await self._fast_return("Okay. Do you have the Order Number?", "ORGANIZE", callback)

        elif status == "HUNTING":
            session.state = "ORGANIZE"
            return await self._fast_return("I'm listening. Go ahead.", "ORGANIZE", callback)

        # Fallback
        return await self._generate_llm_response(session, "CLARIFY", text, callback)

    async def _phase_order(self, session: CallSession, text: str, callback):
        status, new_buf, data = self.parser.parse(text, session.parser_buffer)
        session.parser_buffer = new_buf

        if status == "LOCKED":
            session.context.order_id = data
            return await self._fetch_and_educate(session, callback)
        
        if status == "HUNTING":
            return {"text": "", "status": "hunting", "scenario": session.state} # Silence
        
        # If chatting but no numbers
        if len(text.split()) > 2 and not any(c.isdigit() for c in text):
            return await self._generate_llm_response(session, "ASK_ORDER", text, callback)
        
        return await self._generate_llm_response(session, "CLARIFY", text, callback)

    async def _phase_educate(self, session: CallSession, text: str, callback):
        return await self._generate_llm_response(session, "EXECUTE", text, callback)

    async def _phase_reinforce(self, session: CallSession, text: str, callback):
        # Check for finish (Tier 1/2 handled checks, but specific "Bye" logic is good here)
        # Using Cortex helper for specific "Finished" trigger if not caught by Cascade
        # (Though usually Tier 2 "Passive" or Tier 1 "Stop" might catch some, explicit check is safe)
        if "bye" in text.lower() or "thank" in text.lower():
             return await self._fast_return("Thank you for choosing Home Depot. Goodbye!", "REINFORCE", callback)
             
        return await self._generate_llm_response(session, "EXECUTE", text, callback)

    # --- HELPERS ---

    async def _fetch_and_educate(self, session, callback):
        try:
            session.context.order_details = OmniCorpDB.get_order(session.context.order_id)
        except Exception as e:
            session.context.order_details = {"error": "DB_OFFLINE"}
            
        session.state = "EDUCATE"
        return await self._fast_return(f"I found order {session.context.order_id}. Let me look that up.", "EDUCATE", callback)

    async def _generate_llm_response(self, session: CallSession, mode: str, text: str, callback):
        policy = self.cortex.retrieve_policy(text)
        
        # Build Prompt
        full_log = "\n".join([f"{m.role}: {m.content}" for m in session.history[-10:]])
        directives = self.cortex.get_directive(session.state)
        
        prompt = dedent(f"""
        [INST] You are Saiko, a Home Depot Agent. State: {session.state}. 
        Directive: {directives}
        Policy: {policy}
        Log: {full_log}
        Reply as Saiko: [/INST]""")
        
        resp_text = ""
        try:
            # 🚨 ABORT CHECK INSIDE GENERATION LOOP
            session.abort_signal = False 
            
            for token in self.llm.stream_generate(prompt):
                if session.abort_signal:
                    logger.warning("🛑 ABORT SIGNAL RECEIVED DURING GENERATION")
                    return {"text": resp_text, "status": "stopped"}
                
                # CoT Filter
                if "[THOUGHT]" in token or "[RESPONSE]" in token: continue
                
                if callback: await callback(token)
                resp_text += token
                await asyncio.sleep(0)
                
            session.history.append(ChatMsg("SAIKO", resp_text))

            return {"text": resp_text, "scenario": session.state, "status": "complete"}
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return await self._fast_return("System error. Please hold.", session.state, callback)

    async def _fast_return(self, text, state, callback):
        if callback:
            for i in range(0, len(text), 4):
                await callback(text[i:i+4])
                await asyncio.sleep(0.02)
        return {"text": text, "scenario": state}