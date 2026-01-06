import os
import datetime
import json

class InteractionLogger:
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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Clean up content for single line log if it's too long, or keep multiline if needed
        # For readability, we might want to keep newlines but indent them
        clean_content = str(content)
        
        log_entry = f"[{timestamp}] [{sender} -> {receiver}] ({msg_type}): {clean_content}\n"
        
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
