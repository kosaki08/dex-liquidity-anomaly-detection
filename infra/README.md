## Terraform ルート構成

- 環境別に 2 つのルートディレクトリを用意
  - `infra/envs/dev`: 開発用
  - `infra/envs/prod`: 本番用
- `backend.tf` は GCS バケット共通、`prefix = dev|prod` で state を分離
- 共通モジュールは `infra/modules/*` に格納し、相対パスで呼び出す

### 今後の拡張

- Composer などのサービスを本番で常時稼働させるタイミングで prod プロジェクトを新規作成する
