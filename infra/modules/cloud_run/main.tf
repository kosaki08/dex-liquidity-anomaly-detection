resource "google_cloud_run_v2_service" "default" {
  project  = var.project_id
  name     = var.name
  location = var.location

  template {
    max_instance_request_concurrency = var.concurrency

    containers {
      image = var.image

      # コンテナの待ち受けポート
      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }

    scaling {
      max_instance_count = 1
    }

    # VPCコネクタ設定
    dynamic "vpc_access" {
      for_each = var.vpc_connector != null ? [var.vpc_connector] : []
      content {
        connector = vpc_access.value
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

# v2リソースのIAM設定
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.location
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
