# G検定問題集
G検定（JDLA Deep Learning for GENERAL）の学習向け四択クイズアプリです。  
**現在の主経路は Backend/Frontend 分離ランタイム**です。

- Backend: `backend/app/main.py`（HTTP API）
- Frontend: `frontend/src/index.html`（API駆動UI）
- 問題資産: `gtest_quiz` / `bank/question_bank.jsonl`

---

## 特徴（現行ランタイム）

- **公式シラバス（2024 v1.3）に準拠した問題資産**
- **ユーザー登録/ログイン + トークン認証API**
- **適応出題**（未回答優先 → 弱点章優先 → 章バランス）
- **回答結果とユーザー統計の永続化（SQLite）**
- **CI品質ゲート + E2Eスモーク + リリースチェック**

> 注: 旧来のオンライン生成系（Gemini）資産はリポジトリ内に残っていますが、
> 現行の実行主経路は本README記載の Backend/Frontend split runtime です。

---

## 必要環境

- **Python 3.10 以上**
- ローカルで `pip install -r requirements.txt` が可能な環境

---

## インストール

```bash
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
