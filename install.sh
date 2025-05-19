#!/bin/sh
# uv を使用してインストールするためのスクリプト

set -e

# 現在のディレクトリにインストール（開発モード）
echo "Google Meet Recording Mover をインストールしています..."

if ! command -v uv &> /dev/null
then
    echo "uv がインストールされていません。インストールしてから再度実行してください。"
    echo "インストール方法: https://github.com/astral-sh/uv"
    exit 1
fi

# インストール実行
uv pip install -e .

echo "インストールが完了しました！"
echo "以下のコマンドで実行できます: gmeet-rec-mover"