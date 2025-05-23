## Terraform 構成とワークスペース運用

- すべての Terraform コードは **`infra/`** 配下に集約。
- **実行時の環境 (dev / prod)** は
  1. `terraform workspace`（= backend の state 階層用）
  2. CLI 変数 **`-var env_suffix=${WORKSPACE}`** → `local.env_suffix`（= リソース名・IAM 条件切替用）
     の **２層で判定** します。
- **state の分離**: `backend.tf` にて

  ```hcl
  prefix = "dex-liquidity/${terraform.workspace}"
  ```

  とし、work space ごとにディレクトリを分離。

- 環境固有値（`project_id`, `artifacts_bucket` など）は **`locals.tf`** 内で

  ```hcl
  locals {
    env_suffix = var.env_suffix != "" ? var.env_suffix : terraform.workspace
    project_id = local.env_suffix == "prod"
      ? "portfolio-dex-prod-460122"
      : "portfolio-dex-dev"
    # …略…
  }
  ```

## CI/CD ワークフロー

| ブランチ / イベント                   | WORKSPACE | 処理                              | 備考                                             |
| ------------------------------------- | --------- | --------------------------------- | ------------------------------------------------ |
| **feature → dev Pull Request**        | `dev`     | `terraform plan` + `apply` (自動) | `-var env_suffix=dev`                            |
| **dev → main Pull Request (Release)** | `prod`    | `terraform plan` のみ             | `-var env_suffix=prod`                           |
| **main / workflow_dispatch**          | `prod`    | `terraform apply` (手動)          | `-var env_suffix=prod AUTOAPPROVE=-auto-approve` |

> GitHub Actions では、既存ステップに
>
> ```bash
> -var "env_suffix=${{ inputs.workspace || env.TF_WORKSPACE }}"
> ```
>
> を付与すれば同期が取れます。

---

## Makefile での操作

`WORKSPACE` 変数（デフォルト `dev`）を変えるだけで **workspace と env_suffix が連動** します。

```bash
# 初期化
make init                                # terraform init
make init INIT_FLAGS="-upgrade"          # provider 更新
make init INIT_FLAGS="-reconfigure"      # backend 変更時

# 検証
make validate                            # terraform validate -var env_suffix=dev

# 差分確認
make plan                                # dev
make plan WORKSPACE=prod                 # prod

# 反映
make apply WORKSPACE=dev                 # プロンプトあり
make apply WORKSPACE=dev AUTOAPPROVE=-auto-approve
make apply WORKSPACE=prod                # prod は二重確認ガード
```

---

## Secret のローテーション

```bash
echo -n "NEW_PASSWORD" \
  | gcloud secrets versions add snowflake-pass --data-file=-
```

---

## 今後の拡張予定

- Composer を常時稼働させるタイミングで **prod 専用 GCP プロジェクトを新設**し、
  `project_id` を locals で切替できるよう変数化を検討。
- Vertex AI 導入時には **`env_suffix` をそのまま流用**し、
  Cloud Run ↔︎ Vertex Pipelines のハイブリッド構成を無停止で移行。
