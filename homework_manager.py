import streamlit as st
import gspread
from google.oauth2 import service_account
import json
import os
from dotenv import load_dotenv

# Load env file for standalone/bot usage
load_dotenv()

class HomeworkManager:
    def __init__(self):
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
                # Use secrets if available
                self.sheet_name = st.secrets.get("SHEET_NAME", "JDoit_Homework")
            except:
                self.sheet_name = "JDoit_Homework"

    def connect(self):
        """Connects to Google Sheets using either st.secrets or a local JSON key file."""
        if self.client is None:
            creds_info = None
            try:
                import streamlit as st
                # 1. Standard approach that usually works in Streamlit Cloud
                if "gcp_service_account" in st.secrets:
                    creds_info = st.secrets["gcp_service_account"]
                # 2. Fallback to flat secrets
                elif "private_key" in st.secrets:
                    creds_info = dict(st.secrets)
            except:
                pass

            # 3. Fallback to local file (for Bot environment)
            if not creds_info:
                if os.path.exists("service_account.json"):
                    with open("service_account.json", "r") as f:
                        creds_info = json.load(f)

            try:
                if not creds_info:
                    raise ValueError("Credentials not found in st.secrets or service_account.json")

                # Convert to plain dict to avoid any Streamlit internal class issues
                creds_dict = {}
                try:
                    # If it's a Streamlit Secrets object, convert to dict
                    if hasattr(creds_info, "to_dict"):
                        creds_dict = creds_info.to_dict()
                    else:
                        creds_dict = dict(creds_info)
                except:
                    creds_dict = creds_info # Fallback if already a dict

                # Just in case, fix escaped newlines if they exist
                if isinstance(creds_dict.get("private_key"), str):
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                creds = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
                print(f"DEBUG: Successfully connected to {self.sheet_name}")
            except Exception as e:
                print(f"DEBUG: Connection failed: {e}")
                raise e

    def get_user_info(self, user_id):
        self.connect()
        if not self.sheet: return None
        try:
            records = self.sheet.get_all_records()
            for record in records:
                if str(record.get('user_id')) == str(user_id):
                    return record
        except Exception as e:
            print(f"Error fetching user info: {e}")
        return None

    def get_homework(self, day):
        self.connect()
        try:
            homework_sheet = self.client.open(self.sheet_name).worksheet("Homework")
            all_homework = homework_sheet.get_all_records()
            print(f"DEBUG: Found {len(all_homework)} total homework rows.")
            
            day_homework = [row for row in all_homework if str(row.get('day')).strip() == str(day).strip()]
            print(f"DEBUG: Found {len(day_homework)} rows for Day {day}")
            return day_homework
        except Exception as e:
            print(f"DEBUG: Error in get_homework: {e}")
            return []
