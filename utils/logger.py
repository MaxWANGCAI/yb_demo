import os
import datetime
import json

class InteractionLogger:
    _last_log_entry = None
    _last_log_time = None

    def __init__(self, log_path: str = "logs/interactions.log"):
        self.log_path = log_path
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        log_dir = os.path.dirname(self.log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log_interaction(self, sender: str, receiver: str, content: str, msg_type: str = "info"):
        """
        Logs an interaction in a human-readable format.
        Format: [TIMESTAMP] [SENDER -> RECEIVER] (TYPE): CONTENT
        """
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        clean_content = str(content).strip()
        
        # Construct the log content (excluding timestamp for deduplication check)
        log_content_signature = f"[{sender} -> {receiver}] ({msg_type}): {clean_content}"
        
        # Enhanced Deduplication logic: 
        # 1. If the content is identical to the last log entry (regardless of time), skip it.
        # This prevents the exact same initialization sequence from flooding the logs.
        if InteractionLogger._last_log_entry == log_content_signature:
            return

        InteractionLogger._last_log_entry = log_content_signature
        InteractionLogger._last_log_time = now
        
        log_entry = f"[{timestamp}] {log_content_signature}\n"
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write log: {e}")

    def read_logs(self):
        """Reads the entire log file."""
        if not os.path.exists(self.log_path):
            return ""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading logs: {e}"
