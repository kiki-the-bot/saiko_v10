import sys
import os
# Import the config
from config.settings import AgentConfig
from exllamav2 import (
    ExLlamaV2, ExLlamaV2Config, ExLlamaV2Cache_Q4, 
    ExLlamaV2Tokenizer
)
from exllamav2.generator import ExLlamaV2StreamingGenerator, ExLlamaV2Sampler

class SaikoEngine:
      def __init__(self, config: AgentConfig, model_path: str):
          print(f"🏎️ INITIALIZING EXLLAMAV2 ENGINE FROM: {model_path}")

          self.cfg = config
          
          # 1. Configure
          self.llm_config = ExLlamaV2Config()
          self.llm_config.model_dir = model_path
          self.llm_config.prepare()
          self.llm_config.max_seq_len = 4096
        
          # 2. Load Model
          self.model = ExLlamaV2(self.llm_config)
          self.cache = ExLlamaV2Cache_Q4(self.model, lazy=True)
          print("🟢 LOADING WEIGHTS TO GPU...")
          self.model.load_autosplit(self.cache)
        
          # 3. Tokenizer & Generator
          self.tokenizer = ExLlamaV2Tokenizer(self.llm_config)
          self.generator = ExLlamaV2StreamingGenerator(self.model, self.cache, self.tokenizer)
        
          # 4. Settings (Read from Config!) 🧠
          self.settings = ExLlamaV2Sampler.Settings()
          self.settings.temperature = self.cfg.TEMPERATURE
          self.settings.top_k = self.cfg.TOP_K
          self.settings.top_p = self.cfg.TOP_P
          self.settings.token_repetition_penalty = 1.05
          self.settings.stop_strings = ["\nUSER:", "[INST]"]

      def stream_generate(self, prompt, max_new_tokens=250):
        if not prompt.startswith("<s>"):
            prompt = "<s>" + prompt

        input_ids = self.tokenizer.encode(prompt, encode_special_tokens=True)
        self.generator.warmup()
        self.generator.begin_stream(input_ids, self.settings)
        
        generated_tokens = 0
        while True:
            chunk, eos, _ = self.generator.stream()
            generated_tokens += 1
            if chunk: yield chunk
            if eos or generated_tokens > max_new_tokens: break