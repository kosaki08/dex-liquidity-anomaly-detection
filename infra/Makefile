TF_DIR := $(CURDIR)

WORKSPACE ?= dev   # 引数が無ければ dev
AUTOAPPROVE  ?=    # CI で -auto-approve を渡す用
INIT_FLAGS ?=      # 例: "-upgrade -reconfigure"

## 内部ヘルパー
select-workspace:
	@cd $(TF_DIR) && \
	  (terraform workspace list | grep -q $(WORKSPACE) \
	    && terraform workspace select $(WORKSPACE) \
	    || terraform workspace new $(WORKSPACE))

## ---------- モジュール単体テスト ----------
.PHONY: test-modules
test-modules: ## infra/modules/* の test.sh をすべて実行
	for dir in infra/modules/*; do \
	  if [ -x $$dir/test.sh ]; then \
	    echo "▶ Testing $$dir"; \
	    (cd $$dir && ./test.sh); \
	  fi \
	done

## ---------- 一般コマンド ----------
init:  ## terraform init $(INIT_FLAGS)
	cd $(TF_DIR) && terraform init $(INIT_FLAGS)

plan: select-workspace ## terraform plan
	cd $(TF_DIR) && terraform plan

validate: select-workspace ## terraform validate
	cd $(TF_DIR) && terraform validate

apply: guard-prod select-workspace ## terraform apply $(AUTOAPPROVE)
	cd $(TF_DIR) && terraform apply $(AUTOAPPROVE)

destroy: guard-prod select-workspace ## terraform destroy
	cd $(TF_DIR) && terraform destroy

help:  ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?##"}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ---------- 保護ロジック ----------
# prod だけは確認プロンプトを必須に
guard-prod:
ifeq ($(WORKSPACE),prod)
	@read -p "⚠️  本当に PROD に対して操作しますか? (yes/no) " ans; \
	[ "$$ans" = "yes" ] || (echo "中断しました" && exit 1)
endif
