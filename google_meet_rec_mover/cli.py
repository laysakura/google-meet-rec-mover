"""
Google Meet Recording Mover CLI モジュール

このモジュールは、Google Meetの録画セットを管理・移動するためのCLIツールを提供します。
"""

import os
import sys
import re
import shutil
import click
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple, Union
import logging

# Python 3.11未満ではtomliをインポート、それ以上ではtomllib
try:
    import tomllib
except ImportError:
    import tomli as tomllib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("google-meet-rec-mover")

# 定数
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/google-meet-rec-mover.toml")
DEFAULT_SOURCE_DIR = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-sho.nakatani@secdevlab.com/マイドライブ/Meet Recordings")

class RecordingSet:
    """Google Meet録画セットを表すクラス"""
    
    def __init__(self, prefix: str, video_path: Optional[Path] = None, 
                 transcript_path: Optional[Path] = None, 
                 chat_path: Optional[Path] = None,
                 date: Optional[datetime] = None):
        self.prefix = prefix
        self.video_path = video_path
        self.transcript_path = transcript_path
        self.chat_path = chat_path
        self.date = date
        
        # 日付情報を抽出（あれば）
        if date is None:
            self.extract_date_from_prefix()
    
    def extract_date_from_prefix(self):
        """プレフィックスから日付情報を抽出する"""
        # 日付パターン "YYYY MM DD HH:MM" または "YYYY MM DD HH/MM" を探す
        date_pattern = r'(\d{4})\s+(\d{2})\s+(\d{2})\s+(\d{2})[:/](\d{2})'
        match = re.search(date_pattern, self.prefix)
        
        if match:
            year, month, day, hour, minute = map(int, match.groups())
            try:
                self.date = datetime(year, month, day, hour, minute)
            except ValueError:
                logger.warning(f"日付の解析に失敗: {self.prefix}")
                self.date = None
    
    def is_complete(self) -> bool:
        """録画セットが完全かどうかを返す（少なくとも動画があれば完全とみなす）"""
        return self.video_path is not None
    
    def get_status(self) -> str:
        """録画セットの状態を返す"""
        parts = []
        if self.video_path:
            parts.append("動画")
        if self.transcript_path:
            parts.append("議事録")
        if self.chat_path:
            parts.append("チャット")
        
        return f"[{', '.join(parts)}]"
    
    def ensure_video_extension(self) -> Optional[Path]:
        """録画ファイルに.mp4拡張子がない場合は追加する"""
        if not self.video_path:
            return None
        
        # すでに.mp4拡張子がある場合は何もしない
        if self.video_path.suffix.lower() == '.mp4':
            return self.video_path
        
        # 拡張子がない場合は.mp4を追加
        new_path = self.video_path.with_suffix('.mp4')
        try:
            logger.info(f"録画ファイルに.mp4拡張子を追加: {self.video_path} -> {new_path}")
            self.video_path.rename(new_path)
            self.video_path = new_path
            return new_path
        except Exception as e:
            logger.error(f"拡張子の追加に失敗: {e}")
            return self.video_path
    
    def convert_transcript_to_docx(self) -> Optional[Path]:
        """議事録をGDOCからDOCXに変換する"""
        if not self.transcript_path or self.transcript_path.suffix.lower() != '.gdoc':
            return None
        
        from google_meet_rec_mover.gdoc_converter import GdocConverter
        
        try:
            converter = GdocConverter()
            docx_path = converter.convert_to_docx(self.transcript_path)
            
            if docx_path and docx_path.exists():
                # 変換に成功したら、transcript_pathを更新
                self.transcript_path = docx_path
                return docx_path
        except Exception as e:
            logger.error(f"議事録の変換に失敗: {e}")
        
        return None
    
    def move_to(self, destination: Path) -> bool:
        """録画セットを指定した場所に移動する"""
        # 移動先ディレクトリが存在しない場合は作成
        if not destination.exists():
            destination.mkdir(parents=True)
        
        # 日付ディレクトリを作成
        date_str = "unknown_date"
        if self.date:
            date_str = self.date.strftime("%Y%m%d")
        
        date_dir = destination / date_str
        if not date_dir.exists():
            date_dir.mkdir(parents=True)
        
        success = True
        
        # 録画ファイルに.mp4拡張子がない場合は追加
        if self.video_path:
            self.ensure_video_extension()
        
        # 議事録が.gdocの場合は.docxに変換
        original_gdoc_path = None
        if self.transcript_path and self.transcript_path.suffix.lower() == '.gdoc':
            logger.info(f"議事録を.docxに変換中: {self.transcript_path}")
            original_gdoc_path = self.transcript_path
            
            # 議事録を変換
            docx_path = self.convert_transcript_to_docx()
            
            if not docx_path:
                logger.error("議事録の変換に失敗しました。")
                success = False
        
        # 移動するファイルのリストを作成
        files_to_move = []
        
        if self.video_path:
            files_to_move.append(("動画", self.video_path))
        if self.transcript_path:
            files_to_move.append(("議事録", self.transcript_path))
        if self.chat_path:
            files_to_move.append(("チャット", self.chat_path))
        
        # ファイルを移動
        for file_type, source_path in files_to_move:
            try:
                target_path = date_dir / source_path.name
                logger.info(f"{file_type}を移動中: {source_path} -> {target_path}")
                shutil.move(source_path, target_path)
            except Exception as e:
                logger.error(f"{file_type}の移動に失敗: {e}")
                success = False
        
        # 元の.gdocファイルを削除
        if original_gdoc_path and success:
            try:
                logger.info(f"元の.gdocファイルを削除中: {original_gdoc_path}")
                original_gdoc_path.unlink()
            except Exception as e:
                logger.error(f".gdocファイルの削除に失敗: {e}")
                # ファイルの削除に失敗しても、移動自体は成功とみなす
        
        return success
    
    def __str__(self) -> str:
        date_str = ""
        if self.date:
            date_str = self.date.strftime("%Y-%m-%d %H:%M")
            
        return f"{date_str} - {self.prefix} {self.get_status()}"


class Config:
    """設定ファイルを管理するクラス"""
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.source_dir = Path(DEFAULT_SOURCE_DIR)
        self.destinations = {}
        self.load()
    
    def load(self) -> bool:
        """設定ファイルを読み込む"""
        if not self.config_path.exists():
            logger.warning(f"設定ファイルが見つかりません: {self.config_path}")
            self._create_default_config()
            return False
        
        try:
            with open(self.config_path, "rb") as f:
                config_data = tomllib.load(f)
            
            # ソースディレクトリの設定（オプション）
            if "source_dir" in config_data:
                self.source_dir = Path(os.path.expanduser(config_data["source_dir"]))
            
            # 録画セット移動先の設定
            if "destinations" in config_data:
                self.destinations = {name: Path(os.path.expanduser(path)) 
                                    for name, path in config_data["destinations"].items()}
            
            return True
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {e}")
            return False
    
    def _create_default_config(self):
        """デフォルトの設定ファイルを作成する"""
        default_config = """# Google Meet録画移動ツールの設定ファイル

# 録画ファイルのソースディレクトリ（省略時はデフォルト）
source_dir = "~/Library/CloudStorage/GoogleDrive-sho.nakatani@secdevlab.com/マイドライブ/Meet Recordings"

# 録画セットの移動先一覧
[destinations]
python_training = "/Users/sho.nakatani/Library/CloudStorage/Box-Box/shared-secdevlab/Python基礎+脆弱性診断研修プログラム"
# 移動先を追加する例:
# personal = "~/Documents/MeetRecordings"
# work = "~/Work/Meetings"
"""
        # 設定ファイルのディレクトリが存在しない場合は作成
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, "w") as f:
            f.write(default_config)
        
        logger.info(f"デフォルト設定ファイルを作成しました: {self.config_path}")


class RecordingScanner:
    """Google Meetの録画ファイルをスキャンするクラス"""
    
    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
    
    def scan(self) -> List[RecordingSet]:
        """録画ファイルをスキャンして録画セットのリストを返す"""
        if not self.source_dir.exists():
            logger.error(f"ソースディレクトリが見つかりません: {self.source_dir}")
            return []
        
        # すべてのファイルをリストアップ
        all_files = list(self.source_dir.glob("*"))
        logger.debug(f"スキャンしたファイル数: {len(all_files)}")
        logger.debug(f"スキャンしたファイル: {all_files}")
        
        # プレフィックスを特定して録画セットにグループ化
        recording_sets = self._group_files_into_sets(all_files)
        
        # 日付は降順（新しい順）、プレフィックスは昇順でソート
        recording_sets.sort(key=lambda x: (-(x.date.timestamp() if x.date else float('-inf')), x.prefix))
        
        return recording_sets
    
    def _group_files_into_sets(self, files: List[Path]) -> List[RecordingSet]:
        """ファイルをプレフィックスでグループ化して録画セットにする"""
        prefixes = set()
        recording_map = {}
        
        # ファイル名からプレフィックスを抽出
        for file_path in files:
            prefix = self._extract_prefix(file_path.name)
            if prefix:
                prefixes.add(prefix)
        
        # 各プレフィックスに対応するファイルを見つけて録画セットを作成
        for prefix in prefixes:
            video_path = None
            transcript_path = None
            chat_path = None
            
            for file_path in files:
                if prefix in file_path.name:
                    # ファイルタイプを判別
                    if file_path.suffix.lower() == ".mp4" or "Recording" in file_path.name:
                        video_path = file_path
                    elif file_path.suffix.lower() == ".gdoc" or "Gemini によるメモ" in file_path.name:
                        transcript_path = file_path
                    elif (file_path.suffix.lower() == ".txt" and "chat" in file_path.name.lower()) or "Chat" in file_path.name:
                        chat_path = file_path
            
            recording_set = RecordingSet(
                prefix=prefix,
                video_path=video_path,
                transcript_path=transcript_path,
                chat_path=chat_path
            )
            
            # 少なくとも動画があるセットのみ追加
            if recording_set.is_complete():
                recording_map[prefix] = recording_set
        
        return list(recording_map.values())
    
    def _extract_prefix(self, filename: str) -> Optional[str]:
        """ファイル名からプレフィックスを抽出する"""
        # "Recording" または "Chat" の前のテキストをプレフィックスとする
        recording_match = re.search(r'(.+?)(?:～Recording|～Chat)', filename)
        if recording_match:
            return recording_match.group(1).strip()
        return None


@click.command()
@click.option("--config", "-c", default=DEFAULT_CONFIG_PATH, help="設定ファイルのパス")
@click.option("--verbose", "-v", is_flag=True, help="詳細なログを表示する")
def main(config: str, verbose: bool):
    """Google Meet録画セットを管理して移動するツール"""
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    # 設定を読み込む
    config_manager = Config(config)
    logger.info(f"設定ファイルを読み込みました: {config_manager.config_path}")
    logger.debug(f"ソースディレクトリ: {config_manager.source_dir}")
    logger.debug(f"移動先一覧: {config_manager.destinations}")
    
    # 録画ファイルをスキャン
    scanner = RecordingScanner(config_manager.source_dir)
    recording_sets = scanner.scan()
    
    if not recording_sets:
        click.echo("録画セットが見つかりませんでした。")
        return
    
    # 録画セットの一覧を表示
    click.echo(f"\n🎥 Google Meet録画セット一覧 ({len(recording_sets)}件)\n")
    
    for i, recording_set in enumerate(recording_sets):
        click.echo(f"{i + 1}. {recording_set}")
    
    # 移動対象の録画セットを選択
    while True:
        choice = click.prompt("\n移動する録画セットの番号を入力してください（0で終了）", type=int)
        
        if choice == 0:
            click.echo("終了します。")
            return
        
        if 1 <= choice <= len(recording_sets):
            selected_set = recording_sets[choice - 1]
            break
        
        click.echo("無効な選択です。もう一度お試しください。")
    
    # 移動先を選択
    if not config_manager.destinations:
        click.echo("設定ファイルに移動先が定義されていません。")
        click.echo(f"設定ファイル ({config_manager.config_path}) を編集してください。")
        return
    
    click.echo("\n📁 移動先一覧:")
    destinations = list(config_manager.destinations.items())
    
    for i, (name, path) in enumerate(destinations):
        click.echo(f"{i + 1}. {name}: {path}")
    
    # カスタム移動先オプションを追加
    click.echo(f"{len(destinations) + 1}. カスタム移動先を指定")
    
    while True:
        dest_choice = click.prompt("\n移動先の番号を入力してください（0で終了）", type=int)
        
        if dest_choice == 0:
            click.echo("終了します。")
            return
        
        if 1 <= dest_choice <= len(destinations):
            dest_name, dest_path = destinations[dest_choice - 1]
            break
        elif dest_choice == len(destinations) + 1:
            custom_path = click.prompt("移動先のパスを入力してください")
            dest_path = Path(os.path.expanduser(custom_path))
            dest_name = "カスタム"
            break
        
        click.echo("無効な選択です。もう一度お試しください。")
    
    # 録画セットを移動
    click.echo(f"\n⏳ {selected_set.prefix} を {dest_name} ({dest_path}) に移動しています...")
    
    # 録画ファイルに.mp4拡張子がない場合は追加する通知
    if selected_set.video_path and selected_set.video_path.suffix.lower() != '.mp4':
        click.echo("🎬 録画ファイルに.mp4拡張子を追加します...")
    
    # .gdocファイルがあるか確認
    has_gdoc = selected_set.transcript_path and selected_set.transcript_path.suffix.lower() == '.gdoc'
    if has_gdoc:
        click.echo("📄 議事録(.gdoc)を.docxに変換します...")
    
    success = selected_set.move_to(dest_path)
    
    if success:
        has_mp4_added = selected_set.video_path and selected_set.video_path.suffix.lower() == '.mp4'
        
        if has_gdoc and has_mp4_added:
            click.echo("✅ 録画ファイルの拡張子追加、議事録の変換と移動が完了しました！")
        elif has_gdoc:
            click.echo("✅ 議事録の変換と移動が完了しました！")
        elif has_mp4_added:
            click.echo("✅ 録画ファイルの拡張子追加と移動が完了しました！")
        else:
            click.echo("✅ 移動が完了しました！")
    else:
        click.echo("❌ 移動中にエラーが発生しました。詳細はログを確認してください。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        click.echo("\n中断されました。")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)
