import json
import torch
import logging
import os
from sentence_transformers import SentenceTransformer, util
from config.setting import AgentConfig

logger = logging.getLogger("SaikoSystem")

class NeuroCortex:
    def __init__(self, config: AgentConfig):
        self.cfg = config
        logger.info("Cortex: Loading Neural Models...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device=self.cfg.DEVICE)
        
        self._load_knowledge_base()

    def _load_knowledge_base(self):

        config_path = os.path.join(os.getcwd(), "config", "intents.json")
        
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config not found at {config_path}")

            with open(config_path, "r") as f:
                data = json.load(f)
            
            logger.info("CORTEX: Vectorizing Rules into RAM...")
            
            self.urgent_triggers = data.get("URGENT", {})
            self.passive_phrases = data.get("PASSIVE", [])
            self.business_intents = data.get("BUSINESS", {})
            self.policies = data.get("POLICIES", [])
            self.call_flow = data.get("CALL_FLOW", {}) 
            self.cancel_triggers = data.get("URGENT", {}).get("CANCEL", [])
            
            self.urgent_embeds = self._batch_encode(self.urgent_triggers)
            self.passive_embeds = self.encoder.encode(self.passive_phrases, convert_to_tensor=True)
            self.business_embeds = self._batch_encode(self.business_intents)
            self.policy_embeds = self.encoder.encode(self.policies, convert_to_tensor=True)
            
            logger.info("CORTEX: Knowledge Graph Built.")
            
        except Exception as e:
            logger.error(f"CORTEX CRITICAL FAILURE: {e}")
            self.urgent_triggers = {"STOP": ["stop"]}
            self.urgent_embeds = self._batch_encode(self.urgent_triggers)
            self.call_flow = {}

    def _batch_encode(self, phrase_dict):
        return {k: self.encoder.encode(v, convert_to_tensor=True) for k,v in phrase_dict.items()}

    def get_directive(self, state: str) -> str:
        return self.call_flow.get(state, "Follow standard procedure.")

    def analyze_input(self, text: str) -> dict:

        clean_text = text.lower()

        for label, keywords in self.urgent_triggers.items():
            for kw in keywords:
                if kw in clean_text:
                    return {"type": "URGENT", "label": label, "score": 1.0}

        user_emb = self.encoder.encode(text, convert_to_tensor=True)

        for label, anchors in self.urgent_embeds.items():
            score = torch.max(util.cos_sim(user_emb, anchors)[0]).item()
            if score > self.cfg.URGENT_THRESHOLD:
                return {"type": "URGENT", "label": label, "score": score}

        passive_score = torch.max(util.cos_sim(user_emb, self.passive_embeds)[0]).item()
        if passive_score > self.cfg.PASSIVE_THRESHOLD:
            return {"type": "PASSIVE", "label": "AGREEMENT", "score": passive_score}

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
        if torch.max(scores).item() > 0.55: 
            return self.policies[torch.argmax(scores).item()]
        return "Standard Procedure."