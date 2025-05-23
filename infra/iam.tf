# Cloud Run カスタム SA に付与するロール
locals {
  # Cloud Run に必須な role を付与
  sa_roles = {
    bento     = ["roles/logging.logWriter", "roles/monitoring.metricWriter"]
    streamlit = ["roles/logging.logWriter", "roles/monitoring.metricWriter"]
    airflow   = ["roles/logging.logWriter", "roles/monitoring.metricWriter"] # Airflow 用 Cloud Run がある場合
  }

  # flatten して for_each 可能な形に変換
  iam_bindings = {
    for item in flatten([
      for sa_name, roles in local.sa_roles : [
        for role in roles : {
          key     = "${sa_name}-${role}"
          sa_name = sa_name
          role    = role
        }
      ]
    ]) : item.key => item
  }
}

# 動的に IAM を付与
resource "google_project_iam_member" "sa_min_roles" {
  for_each = local.iam_bindings

  project = local.project_id
  role    = each.value.role
  member  = "serviceAccount:${module.service_accounts.emails[each.value.sa_name]}"
}

# Cloud Run の invoker ロールを付与
resource "google_project_iam_member" "composer_run_invoker" {
  project = local.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@cloudcomposer-accounts.iam.gserviceaccount.com"
}

# MLflow 用 GCS バケットにアクセス権限を付与
resource "google_storage_bucket_iam_member" "artifacts_writer_mlflow" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${module.service_accounts.emails["bento"]}" # MLflow 用 SA
}
