# テスト用変数の定義
variables {
  project_id              = "dummy-project"
  region                  = "asia-northeast1"
  subnet_ip_cidr_range    = "10.9.0.0/24"
  connector_ip_cidr_range = "10.8.0.0/28"
}

# モジュールのパスを指定して plan 実行
run "plan_network_module" {
  command = plan

  module {
    source = "../"
  }

  # 出力値チェック: connector_id が空ではない
  assert {
    condition     = length(run.plan_network_module.outputs.connector_id) > 0
    error_message = "connector_id 出力が空です"
  }
}