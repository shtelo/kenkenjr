from __future__ import print_function

import os.path
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from utils import get_path

SCOPES = ['https://www.googleapis.com/auth/drive']


def get_service():
    creds = None
    token_path = get_path('spreadsheets_token')
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = get_path('spreadsheets_credentials')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    service = build('sheets', 'v4', credentials=creds)
    return service


def sheet_read(spreadsheet_id, range_name):
    sheet = get_service().spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', list())
    return values


def sheet_write(spreadsheet_id, range_name, values, value_iput_option='USER_ENTERED'):
    result = get_service().spreadsheets().values().update(spreadsheetId=spreadsheet_id,
                                                          range=range_name,
                                                          valueInputOption=value_iput_option,
                                                          body={'values': values}).execute()
    return result
