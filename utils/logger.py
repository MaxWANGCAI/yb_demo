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
        
        # Clean up content for single line log if it's too long, or keep multiline if needed
        # For readability, we might want to keep newlines but indent them
        clean_content = str(content)
        
        # Construct the log content (excluding timestamp for deduplication check)
        log_content_signature = f"[{sender} -> {receiver}] ({msg_type}): {clean_content}"
        log_entry = f"[{timestamp}] {log_content_signature}\n"
        
        # Deduplication logic: 
        # If the content is identical to the last log and happened within 1 second, skip it.
        if (InteractionLogger._last_log_entry == log_content_signature and 
            InteractionLogger._last_log_time and 
            (now - InteractionLogger._last_log_time).total_seconds() < 1.0):
            return

        InteractionLogger._last_log_entry = log_content_signature
        InteractionLogger._last_log_time = now
        
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
