<<<<<<< ours
# Gtest-Quiz

G検定向けの完全オフライン静的PWAです。日常利用ではPCサーバーを起動せず、iPhoneのホーム画面から起動して、問題演習・学習履歴・復習スケジュールを端末内に保存します。
=======
# G検定問題集
G検定（JDLA Deep Learning for GENERAL）の学習向け四択クイズアプリです。  
**現在の主経路は Backend/Frontend 分離ランタイム**です。
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours

- Backend: `backend/app/main.py`（HTTP API）
- Frontend: `frontend/src/index.html`（API駆動UI）
- 問題資産: `gtest_quiz` / `bank/question_bank.jsonl`
>>>>>>> theirs

## iPhoneで使う
=======

- Backend: `backend/app/main.py`（HTTP API）
- Frontend: `frontend/src/index.html`（API駆動UI）
- 問題資産: `gtest_quiz` / `bank/question_bank.jsonl`
>>>>>>> theirs

<<<<<<< ours
1. `frontend/src/` を GitHub Pages、Cloudflare Pages、Netlify などの静的ホスティングに公開します。
2. iPhoneのSafariで公開URLを開きます。
3. 共有メニューからホーム画面に追加します。
4. 以後はホーム画面アイコンから起動します。
=======

- Backend: `backend/app/main.py`（HTTP API）
- Frontend: `frontend/src/index.html`（API駆動UI）
- 問題資産: `gtest_quiz` / `bank/question_bank.jsonl`
>>>>>>> theirs

<<<<<<< ours
初回アクセス時に `index.html`、`offline-app.js`、`question-bank.json`、PWAアイコンをService Workerがキャッシュします。キャッシュ後は通信がなくても練習できます。

<<<<<<< ours
GitHub Pagesを使う場合は、`.github/workflows/static-pwa-pages.yml` が `frontend/src/` だけを公開します。PagesをGitHub Actions配信に設定すると、公開URLは通常 `https://<owner>.github.io/<repo>/` になります。

## Static App Files
=======
## 特徴（現行ランタイム）

- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**
=======
## 特徴（現行ランタイム）
=======
=======
>>>>>>> theirs

- Backend: `backend/app/main.py`（HTTP API）
- Frontend: `frontend/src/index.html`（API駆動UI）
- 問題資産: `gtest_quiz` / `bank/question_bank.jsonl`
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs

- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**
=======
## 特徴（現行ランタイム）

<<<<<<< ours
<<<<<<< ours
- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。
>>>>>>> theirs

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。
>>>>>>> theirs

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。
>>>>>>> theirs
=======
## 特徴（現行ランタイム）
=======
## 特徴（現行ランタイム）

- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。
>>>>>>> theirs

- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。
>>>>>>> theirs

- `frontend/src/index.html`: iPhone向けPWAシェル
- `frontend/src/offline-app.js`: ブラウザ内学習エンジン
- `frontend/src/question-bank.json`: 静的問題バンク
- `frontend/src/service-worker.js`: オフラインキャッシュ
- `frontend/src/manifest.webmanifest`: PWA manifest
- `frontend/src/pwa-icon-*.png`: iOS/PWAアイコン

## Local Preview

<<<<<<< ours
PCは本番利用には不要ですが、開発中の確認には静的サーバーを使えます。
=======
- **Python 3.10 以上**
- ローカルで `pip install -r requirements.txt` が可能な環境
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs

```bash
python -m http.server 4173 --directory frontend/src
```
=======
>>>>>>> theirs

Open:

```text
http://127.0.0.1:4173/index.html
```

## Data Model

- 回答履歴、復習スケジュール、学習ポリシーはブラウザのlocalStorageに保存されます。
- `エクスポート` で端末内の学習データをJSONとして退避できます。
- `インポート` で退避データを復元できます。
- インポート時の正誤は `question-bank.json` の `correct_index` から再計算されます。

## Learning Policies
=======
>>>>>>> theirs

- `adaptive_mastery_v2`: 弱点、復習期限、難易度適合、未回答優先を組み合わせます。
- `chapter_balanced_v1`: 章ごとの演習量を均します。
- `random_baseline_v1`: ランダム出題です。
=======
>>>>>>> theirs

## Backend Tooling

FastAPIバックエンドは、静的PWAの日常利用には不要です。問題生成、品質検証、OpenAPI契約、ベンチマーク、将来の同期基盤として残しています。

```bash
python -m backend.app.main
uvicorn backend.app.asgi:app --host 127.0.0.1 --port 8000
```

Gemini APIキーは問題生成・補充フローだけで必要です。静的PWAで練習するだけなら不要です。
=======
>>>>>>> theirs

## Regenerate Static Bank

`bank/question_bank.jsonl` を更新したら、`frontend/src/question-bank.json` を再生成します。

```bash
python tools/build_static_pwa_assets.py
```

## Quality Gates

```bash
<<<<<<< ours
python tools/validate_question_bank.py
python tools/benchmark_learning_policy.py --compare
python tools/release_readiness.py
pytest
```
=======
git clone https://github.com/okk4lt0/Gtest-Quiz.git
cd Gtest-Quiz
pip install -r requirements.txt
```


### 環境変数（.env 方式）
```bash
cp .env.example .env
# .env に GEMINI_API_KEY を設定
```

Geminiを使う処理（オンライン生成/問題補充）は `.env` の `GEMINI_API_KEY` を参照します。

## Runtime (Backend/Frontend Split)

### Backend API
```bash
./scripts_run_backend.sh
```

### Frontend
`frontend/src/index.html` をブラウザで開く（または静的配信）し、必要に応じて `window.API_BASE` を設定してください。

### API endpoints
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /quiz/next`
- `POST /quiz/answer`
- `GET /quiz/stats`
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
