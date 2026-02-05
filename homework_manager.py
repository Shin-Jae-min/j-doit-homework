
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import os
import glob

class HomeworkManager:
    def __init__(self, key_file="service_account.json", sheet_name="JDoIt_Homework"):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Determine strict key file path
        if not os.path.exists(key_file):
            # Try to find any json file that looks like a key
            json_files = glob.glob("*.json")
            for f in json_files:
                if "client" not in f and "package" not in f and "tsconfig" not in f:
                     key_file = f
                     break
        
        self.key_file = key_file
        self.sheet_name = sheet_name
        self.client = None
        self.sheet = None

    def connect(self):
        try:
            if os.path.exists(self.key_file):
                logging.info(f"Connecting to Google Sheet with key: {self.key_file}")
                creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_file, self.scope)
            else:
                # Fallback: Try Streamlit Secrets (for Cloud Deployment)
                logging.info("Key file not found. Trying Streamlit Secrets...")
                import streamlit as st
                # Convert the specific secrets section to a dict for oauth2client
                key_dict = dict(st.secrets["gcp_service_account"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, self.scope)

            self.client = gspread.authorize(creds)
            # Use get_worksheet(0) to always open the first sheet regardless of its name
            self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
            logging.info("Connected to Google Sheet")
        except Exception as e:
            logging.error(f"Failed to connect to Google Sheet: {e}")
            raise

    def get_homework(self, day):
        """
        Retrieves ALL homework entries for a specific day.
        Returns a list of dictionaries: [{'text':..., 'audio_url':...}, ...]
        """
        if not self.client:
            self.connect()
        
        try:
            records = self.sheet.get_all_records()
            hw_list = []
            
            # Normalize target day to string
            target_day = str(day).strip()
            
            for record in records:
                # Normalize record day to string for comparison
                record_day = str(record.get('day', '')).strip()
                
                if record_day == target_day:
                    hw_list.append({
                        'text': record.get('text'),
                        'audio_url': record.get('audio_url')
                    })
            return hw_list
            
        except Exception as e:
            logging.error(f"Error fetching homework: {e}")
            return []
