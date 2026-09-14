# Gemini Desk

Gemini APIをバックエンドから呼び出す、個人用のChatGPT風AIチャットアプリです。会話履歴と長期MemoryをSQLiteへ保存し、優先順位に沿って利用可能なモデルへ自動Fallbackします。

## 必要環境

- Python 3.11以上
- Google AI Studioで発行したGemini APIキー

## インストールと起動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` の `GEMINI_API_KEY` にAPIキーを設定してから起動します。

```bash
uvicorn backend.main:app --reload
```

ブラウザで `http://127.0.0.1:8000` を開いてください。APIキーはFastAPIからGeminiへ送るだけで、ブラウザへ返しません。

## Vercelへの公開

このリポジトリはVercelのPythonランタイム用設定を含んでいます。

[VercelへImportして公開する](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FShiro-to215%2FGemini-3.8-TRIAL)

1. VercelにGitHubアカウントでログインします。
2. `Add New...` → `Project` → `Import Git Repository` からこのGitHubリポジトリを選びます。
3. Environment Variablesに `GEMINI_API_KEY` を登録します。値はGoogle AI StudioのAPIキーです。
4. `Deploy` を実行します。

デプロイ後に表示される `https://...vercel.app` がアプリのURLです。ブラウザからGeminiへ直接アクセスせず、Vercel上のFastAPIがAPIキーを保持します。

Vercelのサーバーレス環境ではローカルSQLiteを恒久保存できません。現在は動作確認用として `/tmp/gemini-chat.db` を使用するため、同じインスタンスが生きている間はMemoryと会話を保持できますが、再デプロイやインスタンス交換で消える可能性があります。Memoryと会話を確実に残す公開版には、Vercel Postgres、Supabase、Tursoなどの外部SQLite互換DBへの移行が必要です。

GitHub Pagesは静的ファイルしか実行できず、FastAPI、Gemini APIキー、SQLiteを動かせません。そのためGitHub PagesのURLだけでこのアプリを完結させることはできません。公開URLとしては、Backend込みのVercel URLを使用してください。

## テスト

```bash
pytest -q
python -m py_compile backend/*.py
```

外部APIを消費するテストはなく、Geminiクライアントのエラーを模したテストでモデル選択、リトライ、Fallback、永続化を確認します。

## モデル設定とFallback

`GEMINI_MODELS` にカンマ区切りで優先順位を指定します。初期値は `gemini-3.8-flash`、`gemini-3.7-flash`、`gemini-3.6-flash`、`gemini-3.5-flash` です。実際に利用できるモデルはGoogleの公式ドキュメントとプロジェクトの契約状況に依存するため、必要に応じて `.env` の1か所だけを変更してください。

通常は最初に利用可能なモデルを使い続けます。429やquota、5xxの場合は有限回リトライし、Retry-Afterが示される短い待機は尊重します。解消しない場合はモデルを一定時間 unavailable としてSQLiteへ保存し、次のモデルへ切り替えます。401/403、リクエスト不正、設定不備ではモデルを切り替えず、原因をユーザーへ安全な文面で返します。日次利用回数を自前で推測したり、日本時間0時に状態をリセットしたりはしません。

## Memory

Memoryは現在の会話履歴とは別のSQLiteテーブルで管理します。サイドバーのMemoryから追加・一覧・削除ができ、各リクエストではSystem Instructionと一緒に参考情報としてGeminiへ渡されます。会話の削除とMemoryの削除は独立しています。

## 構成

- `backend/main.py`: FastAPIルートと依存オブジェクト
- `backend/chat.py`: チャットの処理順序を管理
- `backend/conversation.py`: 会話とメッセージの永続化
- `backend/memory.py`: 長期Memoryの永続化
- `backend/model_manager.py`: モデル優先順位と利用状態
- `backend/fallback.py`: 有限リトライとモデル切替
- `backend/gemini_client.py`: Gemini APIとの境界
- `frontend/`: HTML/CSS/JavaScriptのUI

## セキュリティ上の注意

`.env` はGit管理しません。APIキーをソースコードやFrontendへ書かないでください。`.gitignore` には `.env`、Pythonキャッシュ、SQLiteデータベースを登録済みです。ユーザー入力はFrontendで `textContent` として表示し、HTMLとして挿入しません。