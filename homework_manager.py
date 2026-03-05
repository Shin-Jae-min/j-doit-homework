import streamlit as st
import gspread
from google.oauth2 import service_account
import json

class HomeworkManager:
    def __init__(self):
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        self.sheet = None
        # 시트 이름은 Secrets에서 가져오되, 없으면 기본값 사용
        self.sheet_name = st.secrets.get("SHEET_NAME", "JDoit_Homework")

    def connect(self):
        """최신 google-auth 라이브러리를 사용하여 시트에 연결합니다."""
        if self.client is None:
            try:
                creds_info = st.secrets["gcp_service_account"]
                creds = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                # 메인 시트(Users 정보가 있는 첫 번째 탭) 연결
                self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
            except Exception as e:
                st.error(f"구글 시트 연결 실패: {e}")
                raise e

    def get_user_info(self, user_id):
        """사용자의 진도(Day) 정보를 가져옵니다."""
        self.connect()
        records = self.sheet.get_all_records()
        for record in records:
            if str(record.get('user_id')) == str(user_id):
                return record
        return None

    def get_homework(self, day):
        """해당 Day에 맞는 숙제 목록을 'Homework' 탭에서 가져옵니다."""
        self.connect()
        try:
            # 1. 'Homework'라는 이름의 탭을 엽니다.
            homework_sheet = self.client.open(self.sheet_name).worksheet("Homework")
            all_homework = homework_sheet.get_all_records()
            
            day_homework = []
            for row in all_homework:
                # 2. 시트의 'day' 열과 학생의 진도(day)가 일치하는 행만 골라담습니다.
                if str(row.get('day')) == str(day):
                    day_homework.append({
                        "text": row.get('text'),
                        "audio_url": row.get('audio_url')
                    })
            return day_homework
        except Exception as e:
            st.error(f"숙제 데이터를 가져오는 중 오류 발생: {e}")
            return []

    def update_last_active(self, user_id, date_str):
        """마지막 활동 날짜를 업데이트합니다."""
        self.connect()
        cell = self.sheet.find(str(user_id))
        if cell:
            # 보통 C열(3번째 열)이 last_active 칸입니다.
            self.sheet.update_cell(cell.row, 3, date_str)
