# ---------- 必要な API 一覧 ----------
locals {
  required_apis = [
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
    "iamcredentials.googleapis.com",
    "secretmanager.googleapis.com",
    "composer.googleapis.com", # Composer 3
    "compute.googleapis.com",  # VPC / サブネット
    "logging.googleapis.com",  # Cloud Run / Composer ログ
  ]
}

# ---------- API 有効化 ----------
resource "google_project_service" "enabled" {
  for_each = toset(local.required_apis)

  project            = local.project_id
  service            = each.key
  disable_on_destroy = false # state から外れても API を無効化しない
}
