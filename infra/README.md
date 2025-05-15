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

## Terraform 操作 (Makefile ラッパ)

`infra/Makefile` には日常タスクをまとめたターゲットを定義しています。  
ワークスペース（dev / prod）は `WORKSPACE` 変数で切り替えます。省略時は `dev`になります。

```bash
# 1. Provider 初期化（通常の `terraform init`）
make init

# 1-1. Provider プラグインを最新版に更新
make init INIT_FLAGS="-upgrade -reconfigure"

# 1-2. backend 変更時に再初期化 (State 移行や bucket 変更時)
make init INIT_FLAGS="-reconfigure"

# 2. バリデーション
make validate

# 3. 差分確認 (dev)
make plan                   # WORKSPACE=dev がデフォルト

# 4. 変更反映 (dev)
make apply                  # 自動承認 (-auto-approve) はしていません

# 5. 差分確認 (prod)
make plan WORKSPACE=prod

# 6. 変更反映 (prod)  ⚠️ yes と入力しないと進まないガード付き
make apply WORKSPACE=prod
```

### 今後の拡張

- Composer などのサービスを本番で常時稼働させるタイミングで prod プロジェクトを新規作成する
