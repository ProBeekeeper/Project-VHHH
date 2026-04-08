import queue
import threading
import pyttsx3
import re

class TTSManager:
    def __init__(self, airlines_map: dict):
        self.q = queue.Queue() 
        self.airlines_map = airlines_map 
        

        self.is_active = True
        self.current_engine = None
        
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop_immediate(self):
        self.is_active = False
        
        with self.q.mutex:
            self.q.queue.clear()
            
        if self.current_engine:
            try:
                self.current_engine.stop()
            except Exception:
                pass

    def enable(self):
        self.is_active = True

    def _worker(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError: pass

        while True:
            text = self.q.get()
            if text is None: break
            
            if not self.is_active:
                self.q.task_done()
                continue
            
            speak_text = text
            speak_text = re.sub(r'([A-Z]{3})(\d+)', lambda m: f"{self.airlines_map.get(m.group(1), m.group(1))} {m.group(2)}", speak_text)
            speak_text = re.sub(r'(\d+)\.(\d+)', r'\1 decimal \2', speak_text)
            speak_text = speak_text.replace("FL", "Flight Level ")
            speak_text = re.sub(r'\d+', lambda m: " ".join(list(m.group(0))), speak_text)
            
            try:
                self.current_engine = pyttsx3.init()
                self.current_engine.setProperty('rate', 180) 
                voices = self.current_engine.getProperty('voices')
                for voice in voices:
                    vid = voice.id.lower()
                    vname = voice.name.lower()
                    if 'zira' in vname or 'david' in vname or 'en-us' in vid or 'english' in vname:
                        self.current_engine.setProperty('voice', voice.id)
                        break
                        
                if self.is_active:
                    self.current_engine.say(speak_text)
                    self.current_engine.runAndWait()
                    
            except Exception as e: 
                print(f"TTS Error: {e}")
            finally: 
                self.current_engine = None
                self.q.task_done()

    def speak(self, text: str):
        if self.is_active:
            self.q.put(text)