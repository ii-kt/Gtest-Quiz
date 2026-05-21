# Multi-Perspective Review Rounds (Latest)

## Round 1: API Contract Review
- Perspective: クライアントが期待するHTTP意味論の明確性
- Findings:
  - バリデーション失敗とリソース未検出の境界が曖昧だと、クライアントで適切に処理できない。
- Action taken:
  - `selected_index` 不正は 400、`question_id` 不在は 404 を返すよう明確化。
- Result:
  - API利用側がエラー種別を明確に分岐可能。

## Round 2: E2E Coverage Review
- Perspective: CIの `-m e2e` 実行が本当に主経路を検証しているか
- Findings:
  - e2e マーカー漏れ・ケース不足があると false green のリスク。
- Action taken:
  - HTTP E2Eを `@pytest.mark.e2e` で明示。
  - 異常系（invalid selected_index -> 400）をE2Eに追加。
- Result:
  - 正常系と主要異常系の両方を主経路で検証可能。

## Round 3: Frontend UX Robustness Review
- Perspective: ユーザー操作時の失敗耐性
- Findings:
  - エラーメッセージ導線の後退を自動検知できるテストが薄い。
- Action taken:
  - フロント資産テストにエラーハンドリング文言検証を追加。
- Result:
  - UX劣化の回帰検知能力を補強。

## Round 4: Documentation Consistency Review
- Perspective: 実装・運用手順・README の一貫性
- Findings:
  - README内に旧主経路説明が残ると、利用者が起動手順を誤る可能性がある。
- Action taken:
  - READMEを現行主経路（Backend/Frontend split）中心に再構成。
  - 特徴欄を現行実装の機能に揃えて更新。
- Result:
  - 新規利用者の起動導線と実態が一致。

## Round 5: Quality-Gate Scope Review
- Perspective: 回帰検知範囲の網羅性
- Findings:
  - 分離後は `gtest_quiz` のみのカバレッジ監視では不十分。
- Action taken:
  - CI/Releaseの `--cov` 対象を `backend/app` まで拡張済みであることを確認。
  - Release Runbookの品質ゲート手順を同条件で固定。
- Result:
  - 分離後ランタイムの中核コードも品質ゲート対象として継続監視可能。
