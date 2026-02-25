import sqlite3
import json
import os
from datetime import datetime


class PrintLogger:
    def __init__(self, db_path="print_history.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        # Creating a table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS ai_logs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           timestamp
                           DATETIME,
                           filename
                           TEXT,
                           progress
                           INTEGER,
                           check_type
                           TEXT,
                           status
                           TEXT,
                           confidence
                           REAL,
                           action_taken
                           TEXT,
                           raw_json
                           TEXT
                       )
                       """)
        conn.commit()
        conn.close()

    def log_check(self, check_type, printer_status, ai_data, action_taken):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = printer_status.get("filename", "unknown")
        progress = int(printer_status.get("progress", 0) * 100)

        # Extraction of data from AI JSON
        status = ai_data.get("print_status", ai_data.get("bed_status", "unknown"))
        confidence = ai_data.get("confidence_score", 0.0)

        # Converts the entire AI JSON back to text so that we have a detailed record for possible debugging.
        raw_json = json.dumps(ai_data)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO ai_logs (timestamp, filename, progress, check_type, status, confidence, action_taken,
                                            raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       """, (timestamp, filename, progress, check_type, status, confidence, action_taken, raw_json))

        conn.commit()
        conn.close()
        print(f"📝 Saved: {check_type} ({action_taken})")