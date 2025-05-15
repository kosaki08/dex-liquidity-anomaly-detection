## Terraform 構成とワークスペース運用

- すべての Terraform コードは **`infra/`** 配下にまとめ、`terraform.workspace`（dev/prod）で環境ごとに分岐
- **state の分離** は GCS backend の `prefix = "dex-liquidity"` ＋ワークスペース名で階層化
- 環境固有の値（project_id, artifacts_bucket など）は **`locals.tf`** で `terraform.workspace == "prod"` を条件に切り替え

```text
infra/
├ backend.tf      ← GCS backend 定義 (prefix 固定)
├ versions.tf     ← required_providers
├ providers.tf    ← provider インスタンス設定
├ variables.tf    ← 変数宣言 (env依存以外)
├ locals.tf       ← project_id, artifacts_bucket, region の切替
├ main.tf         ← リソース/モジュール呼び出し
└ Makefile        ← init/plan/apply をラップ
```

## CI/CD ワークフロー

- **feature → dev** PR：`WORKSPACE=dev` で自動 apply + 統合テスト
- **dev → main (Release PR)**：`WORKSPACE=prod` で plan のみ実行
- **本番反映**：`workflow_dispatch`（手動）＋`WORKSPACE=prod AUTOAPPROVE=-auto-approve`

## Terraform 操作 (Makefile ラッパ)

`infra/Makefile` には日常タスクをまとめたターゲットを定義しています。  
ワークスペース（dev / prod）は `WORKSPACE` 変数で切り替えます。省略時は `dev`になります。

```bash
# infra ディレクトリで

# 1. Provider プラグイン初期化
make init

# 1-1. プラグインを最新版へ更新
make init INIT_FLAGS="-upgrade -reconfigure"

# 2. 変数・構文検証
make validate

# 3. 差分確認 (dev)
make plan                            # = make plan WORKSPACE=dev

# 4. 変更反映 (dev)
make apply WORKSPACE=dev             # プロンプトあり
make apply WORKSPACE=dev AUTOAPPROVE=-auto-approve  # プロンプト無し

# 5. 差分確認 (prod)
make plan WORKSPACE=prod

# 6. 変更反映 (prod)
make apply WORKSPACE=prod            # prod はガード付き
# or 手動ワークフローで
make apply WORKSPACE=prod AUTOAPPROVE=-auto-approve
```

## Secret のローテーション方法

Snowflake パスワードを更新する場合は以下のコマンドを実行します。

```bash
echo -n "new_password" \
  | gcloud secrets versions add snowflake-pass --data-file=-
```

### 今後の拡張

- Composer などのサービスを本番で常時稼働させるタイミングで prod プロジェクトを新規作成する
