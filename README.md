# Google Meet Recording Mover

Google Meet録画セット（動画・議事録・チャット）を指定した場所に移動するためのCLIツールです。

## 機能

- Google Driveから録画セット（動画・議事録・チャット）を検出
- 最新の録画から順にリスト表示
- 選択した録画セットを指定した場所に移動

## インストール方法

uvを使用してインストールするには、以下のコマンドを実行します：

```bash
# インストールスクリプトを実行
./install.sh

# または直接uvでインストール
uv pip install -e .
```

## 使い方

インストール後は、`gmeet-rec-mover` コマンドで実行できます：

```bash
# 基本的な使い方
gmeet-rec-mover

# 詳細なログを表示
gmeet-rec-mover --verbose

# 別の設定ファイルを使用
gmeet-rec-mover --config /path/to/config.toml
```

## 設定

初回実行時に `~/.config/google-meet-rec-mover.toml` に設定ファイルが生成されます。
このファイルを編集して、録画元のディレクトリや移動先を設定できます。

### 設定例

```toml
# Google Meet録画移動ツールの設定ファイル

# 録画ファイルのソースディレクトリ（省略時はデフォルト）
source_dir = "~/Library/CloudStorage/GoogleDrive-yourname@example.com/マイドライブ/Meet Recordings"

# 録画セットの移動先一覧
[destinations]
python_training = "/Users/yourname/Library/CloudStorage/Box-Box/shared-xxx/ddd"
personal = "~/Documents/MeetRecordings"
work = "~/Work/Meetings"
```

## プロジェクト構成

```
google-meet-rec-mover/
├── pyproject.toml        # プロジェクト設定
├── install.sh            # インストールスクリプト
├── README.md             # このファイル
└── google_meet_rec_mover/
    ├── __init__.py       # パッケージ初期化
    └── cli.py            # CLIツールのメイン実装
```

## 要件

- Python 3.8以上
- 必要なパッケージ:
  - click
  - tomli (Python 3.11未満の場合のみ)
