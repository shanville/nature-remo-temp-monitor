<!-- README.md / 温度監視ツール一式の使い方メモ。迷子防止のための方角説明。 -->

# 21_home_temp

Nature Remo から取得した室温を Turso に保存し、Streamlit ダッシュボードで可視化する小さな監視アプリです。GitHub Actions で 5 分おきにデータ収集をキックし、ローカルからは Streamlit を起動して確認します。

## セットアップ手順

1. **Python 環境**: プロジェクト直下で `uv sync` を実行すると `.venv` や依存関係が作成されます。
2. **環境変数**: `.env` を複製/更新して以下を設定してください。
   - `NATURE_REMO_API_KEY`
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
3. **確認**: `uv run python main.py` を実行して Nature Remo API から応答が返るか確認します。

## ローカル実行とテスト

- **スケジューラと同じ挙動を再現**: `uv run python collect_data.py`
- **ユニットテスト**: `uv run python -m unittest discover -s tests -t .`
- **可視化アプリ**: `uv run streamlit run app.py`

テストでは API レスポンスと Turso への書き込みパスをモックしているため、 secrets を持たない環境でも実行できます。

## GitHub Actions

- ワークフロー: `.github/workflows/collect_temperature.yml`
- スケジュール: 5 分おきに `collect_data.py` を実行し DB に保存します。
- 手動実行: `workflow_dispatch` から即時実行が可能です。
- 収集ジョブの前に `python -m unittest` を走らせ、最低限のリグレッションを検出するようにしています。

## トラブルシューティング

- **API キーの権限**: Nature Remo クラウド側で `GET /1/devices` が許可されているか確認。
- **Turso 接続失敗**: URL/トークンを再発行した場合は GitHub Secrets も忘れず更新。
- **データが Streamlit に表示されない**: `temperature_logs` テーブルに行が存在するか `libsql` CLI でチェックし、タイムゾーンも JST に変換されていることを確認。

## ディレクトリの目印

- `config.py`: ランタイム設定と定数。
- `collect_data.py`: Nature Remo → Turso への ETL。
- `app.py`: Streamlit ダッシュボード。
- `tests/`: ユニットテスト一式。

実装を触るときは `config.py` に値を追加し、 magic number や URL を各ファイルに散らさないようにしてください。
