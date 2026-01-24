import asyncio
from email.mime import text
import uuid
import logging
from datetime import datetime
from typing import List
from dataclasses import dataclass, field
from textwrap import dedent

from requests import session
from src.data.ammo import ChatMsg, ContextData
#from src.data.database import OmniCorpDB
from src.core.crm_client import CRMClient 
from src.core.cortex import NeuroCortex
from src.core.parser import ChaosParser
from src.core.engine import SaikoEngine 

logger = logging.getLogger("SaikoSystem")

@dataclass
class CallSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state: str = "DISCOVERY"
    history: List[ChatMsg] = field(default_factory=list)
    context: ContextData = field(default_factory=ContextData)
    abort_signal: bool = False
    parser_buffer: str = ""

class SaikoController:

    def __init__(self, cortex: NeuroCortex, llm: SaikoEngine, parser: ChaosParser):
        self.cortex = cortex
        self.llm = llm
        self.parser = parser
        self.crm = CRMClient(provider="SQLITE_MOCK")

    async def process_turn(self, session: CallSession, inbound_msg: ChatMsg, stream_callback):

        session.history.append(inbound_msg)
        text = inbound_msg.content
        logger.info(f"🎮 Session {session.session_id} [{session.state}]: {text}")

        analysis = self.cortex.analyze_input(text)
        logger.info(f"🧠 Cortex Analysis: {analysis}")

        if analysis['type'] == "URGENT":
            if analysis['label'] == "STOP":
                logger.warning("🛑 USER ORDERED STOP")
                session.abort_signal = True 
                return await self._fast_return(session, "Stopping.", session.state, stream_callback)
            
            elif analysis['label'] == "ESCALATE":
                session.state = "EDUCATE"
                session.context.intent = "ESCALATION"
                logger.info("🚨 Escalate -> EDUCATE")
            
            elif analysis['label'] == "CORRECTION":
                session.state = "ORGANIZE"
                session.context.order_id = None
                return await self._fast_return(session,"Apologies. Let's start over.", "ORGANIZE", stream_callback)
            
            elif analysis['label'] == "CANCEL":
                if session.context.order_id and session.context.is_verified:
                    session.state = "CONFIRM_CANCEL"
                return await self._fast_return(session, "Are you sure you want to cancel this order? This cannot be undone.", "CONFIRM_CANCEL", stream_callback)
            elif session.context.order_id:
                session.state = "AUTH_CHALLENGE" 
                return await self._fast_return(session, "To proceed with the cancellation I will need to verify the last 4 digits of your phone number", "AUTH_CHALLENGE", stream_callback)
            else:
                session.state = "ORGANIZE"
                session.context.intent = "CANCEL"
                return await self._fast_return(session, "I can help with that. What's the Order ID?", "ORGANIZE", stream_callback)

        elif analysis['type'] == "PASSIVE":
            resp = "Anything else?" if session.state == "REINFORCE" else "Go on."
            return await self._fast_return(session, resp, session.state, stream_callback)

        elif analysis['type'] == "INTENT":
            if session.state == "REINFORCE":
                logger.info(f"🔀 Re-opening case for {analysis['label']}")
                session.state = "EDUCATE"
                session.context.intent = analysis['label']
            else:
                session.context.intent = analysis['label']
            
        if session.state == "AUTH_CHALLENGE":
            return await self._pin_extraction(session, text, stream_callback)
        if session.state == "CONFIRM_CANCEL":
            return await self._phase_execution(session, text, stream_callback)
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

        status, new_buf, data = self.parser.parse(text, session.parser_buffer)
        session.parser_buffer = new_buf
        
        if status == "LOCKED":
            session.context.order_id = data
            logger.info(f"Order ID Found: {data}")

        if session.context.order_id and session.context.intent:
            return await self._fetch_and_educate(session, callback)
        
        elif session.context.order_id:
            session.context.intent = "STATUS"
            return await self._fetch_and_educate(session, callback)

        elif session.context.intent:
            session.state = "ORGANIZE"
            return await self._fast_return(session, "Okay. Do you have the Order Number?", "ORGANIZE", callback)

        elif status == "HUNTING":
            session.state = "ORGANIZE"
            return await self._fast_return(session, "I'm listening. Go ahead.", "ORGANIZE", callback)

        return await self._generate_llm_response(session, "CLARIFY", text, callback)

    async def _phase_order(self, session: CallSession, text: str, callback):
        status, new_buf, data = self.parser.parse(text, session.parser_buffer)
        session.parser_buffer = new_buf

        if status == "LOCKED":
            session.context.order_id = data
            return await self._fetch_and_educate(session, callback)
        
        if status == "HUNTING":
            return {"text": "", "status": "hunting", "scenario": session.state} 
        
        if len(text.split()) > 2 and not any(c.isdigit() for c in text):
            return await self._generate_llm_response(session, "ASK_ORDER", text, callback)
        
        return await self._generate_llm_response(session, "CLARIFY", text, callback)

    async def _phase_educate(self, session: CallSession, text: str, callback):
        return await self._generate_llm_response(session, "EXECUTE", text, callback)

    async def _phase_reinforce(self, session: CallSession, text: str, callback):
        if "bye" in text.lower() or "thank" in text.lower():
            return await self._fast_return(session, "Thank you for choosing Home Depot. Goodbye!", "REINFORCE", callback)
        
    async def _phase_execution(self, session: CallSession, text: str, callback):
        clean = text.lower()
        yes_words = ["yes", "yeah", "do it", "sure", "correct", "confirm"]
        no_words = ["no", "wait", "stop", "abort"]

        if any(w in clean for w in yes_words):
            result = self.crm.cancel_order(session.context.order_id)
            
            if result['success']:
                session.state = "REINFORCE"
                session.context.order_details = {"status": "CANCELLED"} 
                return await self._fast_return(session, result['msg'], "REINFORCE", callback)
            else:
                session.state = "EDUCATE"
                return await self._fast_return(session, f"I couldn't cancel it. {result['msg']}", "EDUCATE", callback)

        elif any(w in clean for w in no_words):
            session.state = "EDUCATE"
            return await self._fast_return(session, "Cancellation aborted. Order remains active.", "EDUCATE", callback)

        else:
            return await self._fast_return(session, "Please say 'Yes' to confirm or 'No' to stop.", "CONFIRM_CANCEL", callback)
        
    async def _pin_extraction(self, session: CallSession, text: str, stream_callback):
            raw_digits = "".join(filter(str.isdigit, text))
            
            if len(raw_digits) >= 4:
                clean_pin = raw_digits[-4:]
            else:
                clean_pin = None 

            if clean_pin: 
                is_valid = self.crm.verify_pin(session.context.order_id, clean_pin)
                if is_valid:
                    session.context.is_verified = True
                    session.state = "CONFIRM_CANCEL"
                    return await self._fast_return(session, "I was able to verify you identity, let me proceed with your order", "CONFIRM_CANCEL",stream_callback)
                else:
                    session.state = "ORGANIZE"
                    return await self._fast_return(session, "I'm sorry, that number does not match our records. I cannot authorize this action.", "ORGANIZE", stream_callback)

            else:
                if "cancel" in text.lower() or "stop" in text.lower():
                    session.state = "ORGANIZE"
                    return await self._fast_return(session, "Authorization cancelled.", "ORGANIZE", stream_callback)
                
                return await self._fast_return(session, "I just need the last 4 digits of the phone number whenever you're ready.", "AUTH_CHALLENGE", stream_callback)
            #return await self._generate_llm_response(session, "EXECUTE", text, callback)

    # --- HELPERS ---

    async def _fetch_and_educate(self, session, callback):
        try:
            session.context.order_details = self.crm.get_order_status(session.context.order_id)
        except Exception as e:
            session.context.order_details = {"error": "DB_OFFLINE"}
            
        session.state = "EDUCATE"
        return await self._fast_return(session, f"I found order {session.context.order_id}. Let me look that up.", "EDUCATE", callback)

    async def _generate_llm_response(self, session: CallSession, mode: str, text: str, callback):
        policy = self.cortex.retrieve_policy(text)
        full_log = "\n".join([f"{m.role}: {m.content}" for m in session.history[-10:]])
        directives = self.cortex.get_directive(session.state)
        context_str = session.context.to_prompt_block()
        now = datetime.now()
        current_time = now.strftime("%A, %B %d, %Y at %I:%M %p")

        prompt = dedent(f"""
        [INST] You are Saiko, a Home Depot Agent. State: {session.state}. 
        Directive: {directives}
        {context_str}
        Policy: {policy}
        Current Time: {current_time}
        Log: {full_log}
        Reply as Saiko: [/INST]""")
        
        resp_text = ""
        try:

            session.abort_signal = False 
            
            for token in self.llm.stream_generate(prompt):
                if session.abort_signal:
                    logger.warning("ABORT SIGNAL RECEIVED DURING GENERATION")
                    return {"text": resp_text, "status": "stopped"}
                
                if "[THOUGHT]" in token or "[RESPONSE]" in token: continue
                
                if callback: await callback(token)
                resp_text += token
                await asyncio.sleep(0)
                
            session.history.append(ChatMsg("SAIKO", resp_text))

            return {"text": resp_text, "scenario": session.state, "status": "complete"}
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return await self._fast_return(session, "System error. Please hold.", session.state, callback)

    async def _fast_return(self, session, text, state, callback):
        session.history.append(ChatMsg("SAIKO", text))
        if callback:
            for i in range(0, len(text), 4):
                await callback(text[i:i+4])
                await asyncio.sleep(0.02)
        return {"text": text, "scenario": state}