variables {
  project_id              = "dummy-project"
  region                  = "asia-northeast1"
  subnet_ip_cidr_range    = "10.9.0.0/24"
  connector_ip_cidr_range = "10.8.0.0/28"
}

run "plan_network_module" {
  command = plan

  module {
    source = "../"
  }

  assert {
    condition     = length(run.plan_network_module.outputs.connector_id) > 0
    error_message = "connector_id 出力が空です"
  }
}