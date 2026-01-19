import logging
import torch
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# --- LOGGING ---
logger = logging.getLogger("SaikoSystem")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File Handler
file_handler = logging.FileHandler("saiko_system.log", mode='w', encoding='utf-8')
file_handler.setFormatter(formatter)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if not logger.handlers:
     logger.addHandler(file_handler)
     logger.addHandler(console_handler)

@dataclass
class AgentConfig:
     # --- 🧠 BRAIN SETTINGS ---
     INTENT_CONFIDENCE: float = 0.3
     PASSIVE_THRESHOLD: float = 0.7
     URGENT_THRESHOLD: float = 0.7
     
     # --- 🏎️ ENGINE SETTINGS ---
     # Now your Engine reads these!
     TEMPERATURE: float = 0.7
     TOP_P: float = 0.9
     TOP_K: int = 50
     
     # --- 🎧 AUDIO SETTINGS ---
     # Moved from old config.py
     MIC_ID: int = int(os.getenv("MIC_ID", 1)) # Read from ENV or default to 1
     SPEAKER_ID: int = int(os.getenv("SPEAKER_ID", 0))
     SAMPLE_RATE: int = 16000
     
     # --- 📂 SYSTEM PATHS ---
     MODEL_PATH: str = os.getenv("MODEL_PATH", os.path.join("models", "mistral_nemo"))
     DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"