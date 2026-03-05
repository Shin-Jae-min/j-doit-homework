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
            
            # 1. Try to load from Streamlit Secrets
            try:
                import streamlit as st
                # Option A: [gcp_service_account] header used
                if "gcp_service_account" in st.secrets:
                    creds_info = dict(st.secrets["gcp_service_account"])
                # Option B: Individual keys pasted without header
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
            except Exception as e:
                print(f"DEBUG: st.secrets access failed: {e}")

            # 2. Fallback to local service_account.json (for Bot environment)
            if not creds_info or not creds_info.get("private_key"):
                key_path = "service_account.json"
                if os.path.exists(key_path):
                    try:
                        with open(key_path, "r", encoding="utf-8") as f:
                            creds_info = json.load(f)
                    except:
                        pass

            # Validation & Connection
            try:
                # Extra safety: filter out None values and check for required fields specifically
                creds_info = {k: v for k, v in creds_info.items() if v is not None}
                
                required_fields = ["project_id", "private_key", "client_email", "private_key_id"]
                missing = [f for f in required_fields if f not in creds_info or not creds_info.get(f)]
                if missing:
                    raise ValueError(f"Missing required credential fields in Secrets: {', '.join(missing)}. Please verify your service_account.json content is correctly pasted into Streamlit Secrets.")

                creds = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
            except Exception as e:
                error_msg = f"Spreadsheet connection failed: {e}"
                try:
                    import streamlit as st
                    st.error(error_msg)
                except:
                    print(error_msg)
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
            day_homework = [row for row in all_homework if str(row.get('day')) == str(day)]
            return day_homework
        except Exception as e:
            print(f"Error fetching homework for day {day}: {e}")
            return []
