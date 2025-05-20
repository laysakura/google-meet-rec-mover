"""
Google Docs (.gdoc) to Word (.docx) converter module

このモジュールは、Google Docsファイル(.gdoc)をWord(.docx)に変換する機能を提供します。
"""

from __future__ import print_function
import io
import os.path
import pickle
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from pathlib import Path
import logging

logger = logging.getLogger("google-meet-rec-mover")

class GdocConverter:
    """Google Docsファイル(.gdoc)をWord(.docx)に変換するクラス"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Google Drive APIの認証を行う"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('drive', 'v3', credentials=self.creds)
    
    def extract_file_id(self, gdoc_path):
        """GDOCファイルからGoogle DriveのファイルIDを抽出する"""
        try:
            with open(gdoc_path, 'r') as f:
                data = json.load(f)
                return data.get('doc_id')
        except Exception as e:
            logger.error(f"GDOCファイルの解析に失敗: {e}")
            return None
    
    def convert_to_docx(self, gdoc_path, output_path=None):
        """GDOCファイルをDOCXに変換する"""
        gdoc_path = Path(gdoc_path)
        
        if output_path is None:
            # 出力パスが指定されていない場合は、同じディレクトリに同名で.docx拡張子のファイルを作成
            output_path = gdoc_path.with_suffix('.docx')
        
        # ファイルIDを抽出
        file_id = self.extract_file_id(gdoc_path)
        if not file_id:
            logger.error(f"ファイルIDの抽出に失敗: {gdoc_path}")
            return None
        
        try:
            # DOCXとしてエクスポート
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logger.debug(f"ダウンロード進捗: {int(status.progress() * 100)}%")
            
            logger.info(f"変換完了: {gdoc_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"DOCXへの変換に失敗: {e}")
            return None
