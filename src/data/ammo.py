from dataclasses import dataclass, field, asdict
from typing import Literal, Optional
from datetime import datetime
import json

@dataclass
class ChatMsg: 
     role: Literal["USER", "SAIKO", "SYSTEM"]
     content: str
     reply_q: Optional[str]= field(default=None, repr=False)
     
     # ✅ FIXED: Only defined ONCE. 
     # Auto-fills with "10:30:45" if you don't provide it.
     timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
     
     # ✅ FIXED: Only defined ONCE.
     confidence: float = 1.0
     metadata: dict = field(default_factory=dict)

     @property
     def log_entry(self):
          # Since timestamp is already a string like "10:30:15", we just use it directly
          return f"[{self.timestamp}] {self.role}: {self.content}"
     
     def to_json(self):
          # ✅ FIXED: json.dump writes to file, json.dumps returns a string
          return json.dumps(asdict(self))
     
class ContextData:
     intent: Optional[str] = None
     order_id: Optional[str] = None
     cx_name: Optional[str] = None 
     sentiment: str = "NEUTRAL"
     order_details : Optional[str] = None
     is_verified : bool = False

     def to_prompt_block(self) -> str:
          lines = ["context data:"]
          if self.is_verified:
               lines.append(f" - USER VERIFIED: {self.is_verified}")
          if self.order_id:
               lines.append(f"- ACTIVE ORDER ID: {self.order_id}")
          if self.intent:
               lines.append(f"- INTENT DETECTED: {self.intent}")
          if self.cx_name:
               lines.append(f"- NAME MEMORIZED: {self.cx_name}")
          if self.order_details:
               lines.append(f" - ORDER DETAILS: {self.order_details}")
               lines.append(" - INSTRUCTION: Tell the user exactly what is in the database result.")
     
          if not lines:
               return ""
          
          return "\n [mission brief]:\n" + "\n".join(lines)
     
