import multiprocessing
import numpy as np
import pyaudio
import torch
import collections
import ctypes
import os
import time
import queue
import atexit
import logging
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHUNK_SIZE = 1024 # Hardware chunk
VAD_CHUNK = 512   # Silero chunk
MAX_SILENCE_CHUNKS = 20 # ~1.2 seconds of silence to stop recording
PRE_RECORD_CHUNKS = 10  # Keep 0.6s of audio before trigger
VAD_THRESHOLD_START = 0.75
VAD_THRESHOLD_INTERRUPT = 0.85

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SaikoEars")

def _load_dlls():
    try:
        libs_path = os.path.join(os.getcwd(), "libs") 
        zlib_file = os.path.join(libs_path, "zlibwapi.dll")
        if os.path.exists(zlib_file): ctypes.CDLL(zlib_file)
        if os.path.exists(libs_path): os.add_dll_directory(libs_path)
    except: pass

def audio_capture_worker(output_queue, command_queue, device_id):
    _load_dlls()

    try:
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False, trust_repo=True)
    except Exception as e:
        output_queue.put(("ERROR", f"VAD Load Failed: {e}"))
        return

    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, 
                        input_device_index=device_id, frames_per_buffer=CHUNK_SIZE)
    except Exception as e:
        output_queue.put(("ERROR", f"Mic Error: {e}"))
        return
    
    ring_buffer = collections.deque(maxlen=PRE_RECORD_CHUNKS)
    active_buffer = []
    
    is_speaking = False
    silence_counter = 0
    paused = False 

    logger.info(f"EAR WORKER: Online (PID {os.getpid()})")
    
    while True:
        try:
            while not command_queue.empty():
                cmd = command_queue.get_nowait()
                if cmd == "STOP": 
                    stream.stop_stream(); stream.close(); p.terminate(); return
                elif cmd == "PAUSE": paused = True
                elif cmd == "RESUME": paused = False
        except: pass

        try:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            
            rms = int(np.sqrt(np.mean(audio_int16.astype(np.float32)**2)))
            output_queue.put(("VOLUME", rms))

            if paused: continue

            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            conf_a = model(torch.from_numpy(audio_float32[:VAD_CHUNK]), SAMPLE_RATE).item()
            conf_b = model(torch.from_numpy(audio_float32[VAD_CHUNK:]), SAMPLE_RATE).item()
            confidence = max(conf_a, conf_b)

            if confidence > VAD_THRESHOLD_INTERRUPT and not is_speaking:
                output_queue.put(("INTERRUPT", True))
                is_speaking = True 
                active_buffer.extend(list(ring_buffer)) 
                ring_buffer.clear()

            if confidence > VAD_THRESHOLD_START:
                if not is_speaking:
                    is_speaking = True
                    active_buffer.extend(list(ring_buffer))
                    ring_buffer.clear()
                
                silence_counter = 0
                active_buffer.append(audio_int16)

            elif is_speaking:
                active_buffer.append(audio_int16)
                silence_counter += 1

                if silence_counter > MAX_SILENCE_CHUNKS:
                    output_queue.put(("AUDIO", list(active_buffer)))
                    active_buffer = []
                    is_speaking = False
                    silence_counter = 0

            else:
                ring_buffer.append(audio_int16)
            
        except Exception as e:
            output_queue.put(("ERROR", str(e)))
            break

class SaikoEars:
    def __init__(self, callback_function, volume_callback=None, interrupt_callback=None):
        self.callback = callback_function
        self.volume_callback = volume_callback
        self.interrupt_callback = interrupt_callback
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info(f"EARS: Loading Whisper on {device} ({compute_type})...")
        self.whisper = WhisperModel("distil-large-v3", device=device, compute_type=compute_type)
        
        logger.info("EARS: Warming up GPU kernels...")
        try:
            dummy_audio = np.zeros(16000, dtype=np.float32)
            self.whisper.transcribe(dummy_audio, beam_size=1)
            logger.info("EARS: Warmup Complete.")
        except: pass

        self.audio_q = multiprocessing.Queue()
        self.cmd_q = multiprocessing.Queue()

        dev_id = self._get_default_mic_id()

        self.p = multiprocessing.Process(target=audio_capture_worker, args=(self.audio_q, self.cmd_q, dev_id))

        atexit.register(self.shutdown)

    def _get_default_mic_id(self):
        p = pyaudio.PyAudio()
        try:
            info = p.get_default_input_device_info()
            return info['index']
        except: return 0
        finally: p.terminate()

    def start_listening(self):
        self.p.start()
        import threading
        threading.Thread(target=self._process_loop, daemon=True).start()

    def _process_loop(self):
        while True:
            try:
                packet = self.audio_q.get()
                msg_type, data = packet[0], packet[1]
                
                if msg_type == "AUDIO": 
                    self._transcribe(data)

                elif msg_type == "INTERRUPT":
                    logger.info("🛑 INTERRUPT TRIGGERED")
                    if self.interrupt_callback: self.interrupt_callback()
                
                elif msg_type == "VOLUME":
                    if self.volume_callback: 
                        # Normalize 0-3000 to 0.0-1.0
                        self.volume_callback(min(data / 2000, 1.0))
                        
                elif msg_type == "ERROR": 
                    logger.error(f"AUDIO ERROR: {data}")
                    
            except Exception as e:
                logger.error(f"Ears Loop Error: {e}")

    def _transcribe(self, chunks):
        if not chunks: return
        try:

            audio = np.concatenate(chunks)
            audio_float = audio.astype(np.float32) / 32768.0

            segments, info = self.whisper.transcribe(
                audio_float, 
                beam_size=1, 
                language="en", 
                condition_on_previous_text=False,
                initial_prompt="Transcript of a polite customer service request."
            )
            
            text = " ".join([s.text for s in segments]).strip()

            import re 
            text = re.sub(r'\b(uh|uhh|ahhr|mhm|hm|ehh)\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip()

            ghosts = ["thanks for watching", "thank you", "captioned", "subs by"]

            if not text: return
            
            is_ghost = any(g in text.lower() for g in ghosts)
            if len(text) < 5 and is_ghost:
                return 

            if len(text) > 1:
                self.callback(text, "en")
                
        except Exception as e:
            logger.error(f"Transcription Failed: {e}")

    def shutdown(self): 
        self.cmd_q.put("STOP")
        if self.p.is_alive():
            self.p.join(timeout=1)
            if self.p.is_alive(): self.p.terminate() # Force kill if stubborn
    
    def pause(self): self.cmd_q.put("PAUSE")
    def resume(self): self.cmd_q.put("RESUME")