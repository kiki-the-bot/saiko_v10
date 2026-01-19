import torch
import logging
from sentence_transformers import SentenceTransformer, util

# Import Config
from config.settings import AgentConfig

# Assumed Local Imports (Adjust path if you move knbase.py)
from src.data.knowledge import POLICIES 

logger = logging.getLogger("SaikoSystem")

class NeuroCortex:
    """
    Handles NLU using a Tiered Priority Cascade.
    Urgent > Passive > Intent.
    """
    def __init__(self, config: AgentConfig):
        self.cfg = config
        logger.info("🧠 Cortex: Loading Models & Computing Embeddings...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device=self.cfg.DEVICE)
        
        # TIER 1: URGENT (Control Flow)
        self.urgent_triggers = {
            "ESCALATE": ["human", "manager", "representative", "agent", "supervisor"],
            "STOP": ["stop", "shut up", "cancel", "hold on", "wait", "silence"],
            "CORRECTION": ["wrong number", "mistake", "go back", "not that one", "incorrect"]
        }
        self.urgent_embeds = self._batch_encode(self.urgent_triggers)

        # TIER 2: PASSIVE (Noise Filtering)
        self.passive_phrases = ["uh huh", "yeah", "ok", "go on", "sure", "alright", "i understand"]
        self.passive_embeds = self.encoder.encode(self.passive_phrases, convert_to_tensor=True)

        # TIER 3: BUSINESS INTENTS (Logic)
        self.business_intents = {
            "REFUND": ["refund", "money back", "return", "wrong item", "damaged"],
            "STATUS": ["where is my order", "tracking", "late", "shipping", "not received"],
        }
        self.business_embeds = self._batch_encode(self.business_intents)
        
        # Knowledge Base
        self.policy_embeds = self.encoder.encode(POLICIES, convert_to_tensor=True)

    def _batch_encode(self, phrase_dict):
        return {k: self.encoder.encode(v, convert_to_tensor=True) for k,v in phrase_dict.items()}

    def analyze_input(self, text: str) -> dict:
        """
        Runs the Priority Cascade. 🌊
        Returns: {"type": "URGENT"|"PASSIVE"|"INTENT"|"NONE", "label": str, "score": float}
        """
        user_emb = self.encoder.encode(text, convert_to_tensor=True)

        # 1. CHECK URGENT (Override)
        for label, anchors in self.urgent_embeds.items():
            score = torch.max(util.cos_sim(user_emb, anchors)[0]).item()
            if score > self.cfg.URGENT_THRESHOLD:
                return {"type": "URGENT", "label": label, "score": score}

        # 2. CHECK PASSIVE (Short Circuit)
        passive_score = torch.max(util.cos_sim(user_emb, self.passive_embeds)[0]).item()
        if passive_score > self.cfg.PASSIVE_THRESHOLD:
            return {"type": "PASSIVE", "label": "AGREEMENT", "score": passive_score}

        # 3. CHECK INTENT (Business Logic)
        best_label, best_score = None, 0.0
        for label, anchors in self.business_embeds.items():
            score = torch.max(util.cos_sim(user_emb, anchors)[0]).item()
            if score > best_score:
                best_score, best_label = score, label
        
        if best_score > self.cfg.INTENT_CONFIDENCE:
            return {"type": "INTENT", "label": best_label, "score": best_score}

        return {"type": "NONE", "label": None, "score": 0.0}

    def retrieve_policy(self, text: str) -> str:
        user_emb = self.encoder.encode(text, convert_to_tensor=True)
        scores = util.cos_sim(user_emb, self.policy_embeds)[0]
        if torch.max(scores).item() > 0.4:
            return POLICIES[torch.argmax(scores).item()]
        return "Standard Procedure."