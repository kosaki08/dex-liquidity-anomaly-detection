## Terraform ルート構成

- 環境別に 2 つのルートディレクトリを用意
  - `infra/envs/dev`: 開発用
  - `infra/envs/prod`: 本番用
- `backend.tf` は GCS バケット共通、`prefix = dev|prod` で state を分離
- 共通モジュールは `infra/modules/*` に格納し、相対パスで呼び出す

## Secret のローテーション方法

Snowflake パスワードを更新する場合は以下のコマンドを実行します。

```bash
echo -n "new_password" \
  | gcloud secrets versions add snowflake-pass --data-file=-
```

### 今後の拡張

- Composer などのサービスを本番で常時稼働させるタイミングで prod プロジェクトを新規作成する
