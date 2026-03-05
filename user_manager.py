
import json
import os
import datetime
import logging
import gspread
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load env file for standalone/bot usage
load_dotenv()

class UserManager:
    def __init__(self, db_file="users.json", key_file="service_account.json"):
        self.db_file = db_file
        self.users = self.load_users()
        
        # Google Sheet Config
        self.key_file = key_file
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        self.sheet = None
        
        # 1. Check environment variable first (for Bot)
        # 2. Then check Streamlit secrets (for Web)
        self.sheet_name = os.getenv("SHEET_NAME")
        if not self.sheet_name:
            try:
                import streamlit as st
                self.sheet_name = st.secrets.get("SHEET_NAME", "JDoit_Homework")
            except:
                self.sheet_name = "JDoit_Homework"

    def connect_sheet(self):
        """Connects to 'Users' worksheet using st.secrets or local key file."""
        if self.client is None:
            creds_info = None
            
            # 1. Try Streamlit Secrets
            try:
                import streamlit as st
                if "gcp_service_account" in st.secrets:
                    creds_info = dict(st.secrets["gcp_service_account"])
                elif "private_key" in st.secrets:
                    creds_info = {
                        "type": st.secrets.get("type", "service_account"),
                        "project_id": st.secrets.get("project_id"),
                        "private_key_id": st.secrets.get("private_key_id"),
                        "private_key": st.secrets.get("private_key"),
                        "client_email": st.secrets.get("client_email"),
                        "client_id": st.secrets.get("client_id"),
                        "auth_uri": st.secrets.get("auth_uri"),
                        "token_uri": st.secrets.get("token_uri"),
                        "auth_provider_x509_cert_url": st.secrets.get("auth_provider_x509_cert_url"),
                        "client_x509_cert_url": st.secrets.get("client_x509_cert_url")
                    }
            except:
                pass

            # 2. Fallback to local file
            if not creds_info or not creds_info.get("private_key"):
                if os.path.exists(self.key_file):
                    try:
                        with open(self.key_file, "r", encoding="utf-8") as f:
                            creds_info = json.load(f)
                    except Exception as e:
                        logging.error(f"Failed to read key file: {e}")

            # Validation & Connection
            try:
                if not creds_info:
                    logging.warning("User Manager: No credentials found.")
                    return
                
                # Convert to plain dict
                creds_dict = {}
                try:
                    if hasattr(creds_info, "to_dict"):
                        creds_dict = creds_info.to_dict()
                    else:
                        creds_dict = dict(creds_info)
                except:
                    creds_dict = creds_info

                if isinstance(creds_dict.get("private_key"), str):
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                creds = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                self.sheet = self.client.open(self.sheet_name).worksheet("Users")
            except Exception as e:
                logging.error(f"User Manager connection failed: {e}")
                self.sheet = None

    def sync_to_sheet(self, user_id, current_day, last_updated):
        """Sync a single user's status to Google Sheet."""
        self.connect_sheet()
        if not self.sheet:
            return

        try:
            cell = self.sheet.find(str(user_id))
            if cell:
                self.sheet.update_cell(cell.row, 2, current_day)
                self.sheet.update_cell(cell.row, 3, last_updated)
            else:
                self.sheet.append_row([str(user_id), current_day, last_updated])
        except Exception as e:
            logging.error(f"Sheet Sync Error for {user_id}: {e}")

    def update_user_score(self, chat_id, score):
        """Updates the user's score in the linked Google Sheet (Column D)."""
        self.connect_sheet()
        if not self.sheet:
            return

        try:
            str_id = str(chat_id)
            cell = self.sheet.find(str_id)
            if cell:
                self.sheet.update_cell(cell.row, 4, str(score))
            else:
                logging.warning(f"User {str_id} not found in sheet for score update.")
        except Exception as e:
            logging.error(f"Failed to update score for {chat_id}: {e}")

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
        str_id = str(chat_id)
        if str_id not in self.users:
            today = datetime.date.today().isoformat()
            self.users[str_id] = {
                "current_day": 1,
                "last_homework_date": None
            }
            self.save_users()
            self.sync_to_sheet(str_id, 1, today)
            return True
        return False

    def get_user_progress(self, chat_id):
        str_id = str(chat_id)
        return self.users.get(str_id, {"current_day": 1})

    def advance_user_day(self, chat_id):
        str_id = str(chat_id)
        if str_id in self.users:
            self.users[str_id]["current_day"] += 1
            today = datetime.date.today().isoformat()
            self.users[str_id]["last_homework_date"] = today
            self.save_users()
            self.sync_to_sheet(str_id, self.users[str_id]["current_day"], today)
            return self.users[str_id]["current_day"]
        else:
            self.register_user(chat_id)
            return self.advance_user_day(chat_id)
