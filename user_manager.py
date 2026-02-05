
import json
import os
import datetime
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import glob

class UserManager:
    def __init__(self, db_file="users.json", key_file="service_account.json", sheet_name="JDoIt_Homework"):
        self.db_file = db_file
        self.users = self.load_users()
        
        # Google Sheet Setup
        self.key_file = key_file
        self.sheet_name = sheet_name
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.client = None
        self.sheet = None
        
        # Determine strict key file path (borrowed from HomeworkManager logic)
        if not os.path.exists(self.key_file):
            json_files = glob.glob("*.json")
            for f in json_files:
                if "client" not in f and "package" not in f and "tsconfig" not in f and "users" not in f:
                     self.key_file = f
                     break

    def connect_sheet(self):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_file, self.scope)
            self.client = gspread.authorize(creds)
            # Open the 'Users' worksheet
            # Note: User must create a tab named "Users"
            self.sheet = self.client.open(self.sheet_name).worksheet("Users")
        except Exception as e:
            logging.error(f"Failed to connect to Users sheet: {e}")
            self.sheet = None

    def sync_to_sheet(self, user_id, current_day, last_updated):
        """Sync a single user's status to Google Sheet."""
        if not self.client:
            self.connect_sheet()
        
        if not self.sheet:
            return

        try:
            # 1. Check if user exists
            # We assume user_id is in column 1
            cell = self.sheet.find(str(user_id))
            
            if cell:
                # Update existing row
                # user_id(1), current_day(2), last_updated(3)
                self.sheet.update_cell(cell.row, 2, current_day)
                self.sheet.update_cell(cell.row, 3, last_updated)
            else:
                # Append new row
                self.sheet.append_row([str(user_id), current_day, last_updated])
                
        except Exception as e:
            logging.error(f"Sheet Sync Error for {user_id}: {e}")

    def load_users(self):
        if not os.path.exists(self.db_file):
            return {}
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load users DB: {e}")
            return {}

    def save_users(self):
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save users DB: {e}")

    def register_user(self, chat_id):
        """Register a new user with Day 1 if not exists."""
        str_id = str(chat_id)
        if str_id not in self.users:
            today = datetime.date.today().isoformat()
            self.users[str_id] = {
                "current_day": 1,
                "last_homework_date": None
            }
            self.save_users()
            # Initial Sync
            self.sync_to_sheet(str_id, 1, today)
            return True
        return False

    def get_user_progress(self, chat_id):
        str_id = str(chat_id)
        return self.users.get(str_id, {"current_day": 1})

    def advance_user_day(self, chat_id):
        """Update user's current day by +1 and set last_homework_date."""
        str_id = str(chat_id)
        if str_id in self.users:
            self.users[str_id]["current_day"] += 1
            today = datetime.date.today().isoformat()
            self.users[str_id]["last_homework_date"] = today
            self.save_users()
            
            # Sync to Sheet
            self.sync_to_sheet(str_id, self.users[str_id]["current_day"], today)
            return self.users[str_id]["current_day"]
        else:
            # Auto-register if missing
            self.register_user(chat_id)
            return self.advance_user_day(chat_id)
