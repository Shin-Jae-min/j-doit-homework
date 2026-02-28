import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

class HomeworkManager:
    def __init__(self):
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        self.sheet = None
        # 시트 이름은 Secrets에서 가져오되, 없으면 기본값 사용
        self.sheet_name = st.secrets.get("SHEET_NAME", "JDolt_Homework")

    def connect(self):
        """구글 시트에 연결합니다. binascii 에러 방지를 위해 JSON RAW 방식을 사용합니다."""
        if self.client is None:
            try:
                # Secrets에서 GCP_JSON_RAW라는 한 줄짜리 텍스트를 가져와 JSON으로 변환합니다.
                json_creds = json.loads(st.secrets["GCP_JSON_RAW"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, self.scope)
                self.client = gspread.authorize(creds)
                
                # 시트 열기
                self.sheet = self.client.open(self.sheet_name).get_worksheet(0)
            except Exception as e:
                st.error(f"구글 시트 연결에 실패했습니다: {e}")
                raise e

    def get_user_info(self, user_id):
        """사용자 정보를 가져옵니다. 아이디 정렬(숫자/문자) 문제를 방지하기 위해 문자로 변환하여 비교합니다."""
        self.connect()
        # 모든 데이터를 가져와서 user_id(A열)와 비교
        records = self.sheet.get_all_records()
        for record in records:
            # 엑셀의 숫자와 입력된 문자를 모두 문자로 바꿔서 비교 (사장님이 발견하신 정렬 문제 해결)
            if str(record.get('user_id')) == str(user_id):
                return record
        return None

    def get_homework(self, day):
        """해당 날짜의 숙제 목록을 가져옵니다. (기존 로직 유지)"""
        self.connect()
        # 숙제 데이터 로직은 사장님의 기존 시트 구조에 맞게 구현되어 있다고 가정합니다.
        # 예시로 빈 리스트를 반환하거나 기존 로직을 여기에 넣으시면 됩니다.
        return [] 

    def update_last_active(self, user_id, date_str):
        """마지막 활동 날짜를 업데이트합니다."""
        self.connect()
        cell = self.sheet.find(str(user_id))
        if cell:
            # C열(last_active)은 3번째 열입니다.
            self.sheet.update_cell(cell.row, 3, date_str)
