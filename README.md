# Gtest-Quiz

G検定向けの完全オフライン静的PWAです。日常利用ではPCサーバーを起動せず、iPhoneのホーム画面から起動して、問題演習・学習履歴・復習スケジュールを端末内に保存します。

## iPhoneで使う

1. GitHub Pagesの公開URLをiPhoneのSafariで開きます。
2. 共有メニューから「ホーム画面に追加」を選びます。
3. 以後はホーム画面の「G検定 Quiz」アイコンから起動します。

このリポジトリのPages URLは通常次の形式です。

```text
https://ii-kt.github.io/Gtest-Quiz/
```

初回アクセス時に `index.html`、`offline-app.js`、`question-bank.json`、PWAアイコンをService Workerがキャッシュします。キャッシュ後は通信がなくても練習できます。

## Static App Files

- `frontend/src/index.html`: iPhone向けPWAシェル
- `frontend/src/offline-app.js`: ブラウザ内学習エンジン
- `frontend/src/question-bank.json`: 静的問題バンク
- `frontend/src/service-worker.js`: オフラインキャッシュ
- `frontend/src/manifest.webmanifest`: PWA manifest
- `frontend/src/pwa-icon-*.png`: iOS/PWAアイコン

## Local Preview

PCは本番利用には不要ですが、開発中の確認には静的サーバーを使えます。

```bash
python -m http.server 4173 --directory frontend/src
```

```text
http://127.0.0.1:4173/index.html
```

## Data Model

- 回答履歴、復習スケジュール、学習ポリシーはブラウザのlocalStorageに保存されます。
- `エクスポート` で端末内の学習データをJSONとして退避できます。
- `インポート` で退避データを復元できます。
- インポート時の正誤は `question-bank.json` の `correct_index` から再計算されます。

## Backend Tooling

FastAPIバックエンドは静的PWAの日常利用には不要です。問題生成、品質検証、OpenAPI契約、ベンチマーク、将来の同期基盤として残しています。

Gemini APIキーは問題生成・補充フローだけで必要です。静的PWAで練習するだけなら不要です。

## Regenerate Static Bank

`bank/question_bank.jsonl` を更新したら、`frontend/src/question-bank.json` を再生成します。

```bash
python tools/build_static_pwa_assets.py
```

## Quality Gates

```bash
python tools/validate_question_bank.py
python tools/benchmark_learning_policy.py --compare
python tools/release_readiness.py
pytest
```
