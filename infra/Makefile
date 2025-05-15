TF_DIR := $(CURDIR)

# 引数が無ければ dev
WORKSPACE ?= dev
TFVARS_FILE := $(WORKSPACE).tfvars
INIT_FLAGS ?=   # 例: "-upgrade -reconfigure"

## 内部ヘルパー
select-workspace:
	@cd $(TF_DIR) && \
	  (terraform workspace list | grep -q $(WORKSPACE) \
	    && terraform workspace select $(WORKSPACE) \
	    || terraform workspace new $(WORKSPACE))

## 一般コマンド
init:  ## terraform init $(INIT_FLAGS)
	cd $(TF_DIR) && terraform init $(INIT_FLAGS)

help:  ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?##"}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

plan: select-workspace
	cd $(TF_DIR) && terraform plan

apply: guard-prod select-workspace
	cd $(TF_DIR) && terraform apply

destroy: guard-prod select-workspace
	cd $(TF_DIR) && terraform destroy

## ---------- 保護ロジック ----------
# prod だけは確認プロンプトを必須に
guard-prod:
ifeq ($(WORKSPACE),prod)
	@read -p "⚠️  本当に PROD に対して操作しますか? (yes/no) " ans; \
	[ "$$ans" = "yes" ] || (echo "中断しました" && exit 1)
endif
