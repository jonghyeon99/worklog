# WorkLog

FlaskとPostgreSQLを使用した勤怠・有給休暇管理Webアプリケーションです。

## 使用技術

- Python / Flask
- PostgreSQL
- HTML / CSS / JavaScript
- AWS EC2 (Ubuntu)
- Nginx / Gunicorn（デプロイ予定）

## 実装状況

- [x] データベース設計・テーブル作成
- [x] PostgreSQL接続
- [x] ユーザー新規登録
- [x] ログイン・ログアウト
- [ ] 勤怠記録管理
- [ ] 有給休暇管理
- [ ] ユーザー設定
- [ ] 本番環境へのデプロイ

## ローカル環境のセットアップ

1. Python仮想環境を作成します。
2. `pip install -r requirements.txt` を実行します。
3. `.env.example` を参考に `.env` を作成します。
4. PostgreSQLにデータベースを作成し、`schema.sql` を適用します。
5. `python app.py` でアプリケーションを起動します。

※ PostgreSQLの接続設定は、実行環境に合わせて設定してください。

## データベース

- users
- user_settings
- attendance
- leave_grants
- leave_usage

## 開発状況

現在開発中です。外部公開に必要なセキュリティ対策は今後実装予定です。
