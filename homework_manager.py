import streamlit as st
import gspread
from google.oauth2 import service_account # 최신 라이브러리로 교체
import json

class HomeworkManager:
    def __init__(self):
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        self.sheet = None
        self.sheet_name = st.secrets.get("SHEET_NAME", "JDolt_Homework")

    def connect(self):
        """최신 google-auth 라이브러리를 사용하여 연결 에러를 완벽하게 차단합니다."""
        if self.client is None:
            try:
                # Secrets의 gcp_service_account 딕셔너리를 직접 읽어옵니다.
                creds_info = st.secrets["gcp_service_account"]
                creds = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
            except Exception as e:
                st.error(f"구글 시트 연결 실패: {e}")
                raise e

    def get_user_info(self, user_id):
        """아이디가 숫자든 문자든 완벽하게 찾아냅니다."""
        self.connect()
        records = self.sheet.get_all_records()
        for record in records:
            if str(record.get('user_id')) == str(user_id):
                return record
        return None

    def get_homework(self, day):
        # 사장님의 기존 숙제 로직이 여기에 들어갑니다. (현재는 테스트를 위해 빈 리스트)
        return []
