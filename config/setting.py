import logging
import torch
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SaikoSystem")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler("saiko_system.log", mode='w', encoding='utf-8')
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if not logger.handlers:
     logger.addHandler(file_handler)
     logger.addHandler(console_handler)

@dataclass
class AgentConfig:
     INTENT_CONFIDENCE: float = 0.3
     PASSIVE_THRESHOLD: float = 0.7
     URGENT_THRESHOLD: float = 0.7
     
     TEMPERATURE: float = 0.7
     TOP_P: float = 0.9
     TOP_K: int = 50
     
     MIC_ID: int = int(os.getenv("MIC_ID", 1)) 
     SPEAKER_ID: int = int(os.getenv("SPEAKER_ID", 0))
     SAMPLE_RATE: int = 16000
     
     MODEL_PATH: str = os.getenv("MODEL_PATH", os.path.join("models", "mistral_nemo"))
     DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"