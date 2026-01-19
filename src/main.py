import dearpygui.dearpygui as dpg
import threading
import time
import keyboard  
import os
import ctypes
import csv
from collections import deque
from typing import Optional, List
from datetime import datetime 

# --- IMPORTS (Keep your existing path structure) ---
from src.data.ammo import ChatMsg
from src.bridge import BrainBridge
from src.audio.faster_ears import SaikoEars

# --- CONFIG ---
WINDOW_WIDTH = 550
WINDOW_HEIGHT = 900
METRICS_FILE = "saiko_metrics.csv"

# --- DLL FIX (Keep this global, it's system-level patching) ---
def _load_system_dlls():
    try:
        libs_path = os.path.join(os.getcwd(), "libs") 
        zlib_file = os.path.join(libs_path, "zlibwapi.dll")
        if os.path.exists(zlib_file): ctypes.CDLL(zlib_file)
        if os.path.exists(libs_path): os.add_dll_directory(libs_path)
    except: pass

class SaikoHUD:
    """
    The Main GUI Class.
    Encapsulates all state: No more global variables floating around like loose weights.
    """
    def __init__(self):
        # 1. State Initialization (The "Core")
        self.bridge: Optional[BrainBridge] = None
        self.ears: Optional[SaikoEars] = None
        self.listening: bool = False
        
        # UI State
        self.history = deque(maxlen=200)
        self.current_response_buffer: str = ""
        self.latency_start: float = 0.0
        
        # 2. Setup DPG Context
        dpg.create_context()
        self._setup_ui()
        dpg.create_viewport(title="SAIKO HUD v10 (OOP Edition)", width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        dpg.setup_dearpygui()

    def _setup_ui(self):
        """Define the entire layout here. Tidy room, tidy mind."""
        with dpg.window(tag="Primary Window"):
            
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("SAIKO.OS v10", color=(0, 255, 0))
                dpg.add_spacer(width=20)
                dpg.add_text("STATUS:")
                dpg.add_text("●", tag="status_indicator", color=(255, 0, 0)) # Red default
                dpg.add_text("BOOTING...", tag="status_text", color=(255, 255, 0))
                dpg.add_spacer(width=20)
                dpg.add_text("TARGET LOCK", tag="lbl_scenario", color=(255, 165, 0))

            dpg.add_separator()
            
            # Metrics
            with dpg.group(horizontal=True):
                dpg.add_text("LATENCY:")
                dpg.add_text("0.00s", tag="latency_text")
                dpg.add_spacer(width=20)
                dpg.add_text("CONF:")
                dpg.add_text("0%", tag="lbl_conf")
                dpg.add_progress_bar(tag="vu_meter", default_value=0.0, width=100)
                dpg.add_progress_bar(tag="conf_bar", default_value=0.0, width=100)

            dpg.add_separator()

            # Controls
            with dpg.group(horizontal=True):
                dpg.add_button(label="PAUSE EARS (F9)", callback=self.toggle_ears, tag="toggle_btn", width=200)
                dpg.add_button(label="NEXT CALL (F12)", callback=self.next_call, width=200)

            # Chat Stream
            with dpg.child_window(tag="transcript_child", height=600, border=True):
                dpg.add_group(tag="transcript_group")

            # Input
            dpg.add_input_text(tag="manual_input", label="Manual Input (Enter)", on_enter=True, callback=self.handle_manual_input)

    def start_systems(self):
        """Spin up the heavy lifting threads."""
        _load_system_dlls()
        
        dpg.set_value("status_text", "🧠 LOADING BRAIN...")
        self.bridge = BrainBridge() 
        
        dpg.set_value("status_text", "👂 LOADING EARS...")
        self.ears = SaikoEars(
            callback_function=self.on_hear_user, 
            volume_callback=self.update_volume, 
            interrupt_callback=self.kill_switch
        )
        self.ears.start_listening()
        
        # Hotkeys (Binding methods to keys)
        keyboard.add_hotkey("f9", self.toggle_ears)
        keyboard.add_hotkey("f12", self.next_call)
        
        self.listening = True
        self._update_status_display("✅ SYSTEM ONLINE", (0, 255, 255), (0, 255, 0))

    # --- LOGIC HANDLERS ---

    def _update_status_display(self, text, text_color, dot_color):
        """Helper to update status UI without repeating code"""
        dpg.set_value("status_text", text)
        dpg.configure_item("status_text", color=text_color)
        dpg.configure_item("status_indicator", color=dot_color)

    def toggle_ears(self):
        if not self.ears: return
        
        self.listening = not self.listening
        if self.listening:
            self.ears.resume()
            dpg.set_value("toggle_btn", "PAUSE EARS (F9)")
            self._update_status_display("👂 LISTENING...", (0, 255, 255), (0, 255, 0))
        else:
            self.ears.pause()
            dpg.set_value("toggle_btn", "RESUME EARS (F9)")
            self._update_status_display("zzz PAUSED", (100, 100, 100), (255, 0, 0))

    def next_call(self):
        dpg.delete_item("transcript_group", children_only=True)
        self._update_status_display("♻️ REBOOTING...", (255, 165, 0), (255, 0, 0))
        
        self.history.clear()
        self.current_response_buffer = ""
        
        if self.bridge:
            self.bridge.reset_call()
            
        # Reset Metrics
        dpg.set_value("lbl_scenario", "TARGET LOCK")
        dpg.set_value("lbl_conf", "0%")
        dpg.set_value("conf_bar", 0.0)
        
        time.sleep(0.1)
        self._update_status_display("✨ SYSTEM READY", (0, 255, 0), (0, 255, 0))

    def kill_switch(self):
        """Triggered by 'STOP' or 'SHUT UP'"""
        if not "[INTERRUPT]" in self.current_response_buffer:
            self.current_response_buffer += " [INTERRUPT]"
            dpg.set_value("active_saiko_msg", self.current_response_buffer)
        
        if self.bridge:
            self.bridge.trigger_interrupt()
        
        self._update_status_display("⛔ INTERRUPTED", (255, 0, 0), (255, 0, 0))

    def update_volume(self, level):
        """Callback for the VU meter"""
        dpg.set_value("vu_meter", level)

    def on_hear_user(self, text, lang="en"):
        if not text or len(text.strip()) < 2: return
        
        # Highlander Logic (Reuse Tag)
        if dpg.does_item_exist("active_saiko_msg"):
            dpg.remove_alias("active_saiko_msg")

        timestamp_str = time.strftime("%H:%M:%S")
        self.latency_start = time.time()

        dpg.add_text(f"[{timestamp_str}] YOU: {text}", parent="transcript_group", color=(200, 0, 200), wrap=500)
        
        self.current_response_buffer = f"[{timestamp_str}] SAIKO: "
        dpg.add_text(self.current_response_buffer, parent="transcript_group", color=(0, 255, 127), wrap=500, tag="active_saiko_msg")
        
        self._update_status_display("⚡ THINKING...", (255, 255, 0), (0, 255, 0))
        
        # Send to Brain
        msg = ChatMsg(role="USER", content=text)
        self.history.append(msg)
        if self.bridge:
            self.bridge.send_chat_msg(msg)

    def handle_manual_input(self, sender, app_data):
        text = dpg.get_value("manual_input")
        if text:
            dpg.set_value("manual_input", "")
            self.on_hear_user(text)

    def log_interaction(self, user, saiko, scenario, conf, lat):
        """Logs metrics to CSV"""
        if not os.path.isfile(METRICS_FILE):
            with open(METRICS_FILE, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(["Time", "Lat", "Scenario", "Conf", "USER", "SAIKO"])
        try:
            with open(METRICS_FILE, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([
                    datetime.now().strftime("%H:%M:%S"), f"{lat:.2f}", scenario, conf, user, saiko
                ])
        except: pass

    # --- MAIN LOOP ---
    def run(self):
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)
        
        # Start Systems in Background
        threading.Thread(target=self.start_systems, daemon=True).start()
        
        while dpg.is_dearpygui_running():
            self._update_frame()
            dpg.render_dearpygui_frame()
            
        dpg.destroy_context()

    def _update_frame(self):
        """Polls the bridge for new tokens"""
        if not self.bridge: return
        
        updates = self.bridge.get_updates()
        for type_, payload in updates:
            if type_ == "TOKEN":
                self.current_response_buffer += payload
                dpg.set_value("active_saiko_msg", self.current_response_buffer)
                dpg.set_y_scroll("transcript_child", dpg.get_y_scroll_max("transcript_child"))
            
            elif type_ == "FINAL":
                result = payload
                status = result.get("status", "")
                
                # Handling status codes
                if status == "HUNTING":
                    dpg.set_value("status_text", "🦅 HUNTING...")
                    dpg.configure_item("status_text", color=(255, 140, 0))
                    continue
                elif status == "ABORTED":
                    self._update_status_display("⛔ ABORTED", (255, 0, 0), (255, 0, 0))
                else:
                    self._update_status_display("⚫ WAITING", (0, 255, 255), (0, 255, 0))

                # Update Metrics
                latency = time.time() - self.latency_start
                scenario = result.get("scenario", "D")
                confidence = result.get("confidence", 0)
                
                dpg.set_value("lbl_scenario", f"PHASE :: {scenario}")
                dpg.set_value("conf_bar", confidence / 100.0)
                dpg.set_value("lbl_conf", f"CONFIDENCE: {confidence}%")
                dpg.set_value("latency_text", f"LAT: {latency:.2f}s")
                
                # Log it
                user_txt = self.history[-1].content if self.history else "UNKNOWN"
                self.log_interaction(user_txt, result.get("text", ""), scenario, confidence, latency)

# --- ENTRY POINT ---
if __name__ == "__main__":
    app = SaikoHUD()
    app.run()