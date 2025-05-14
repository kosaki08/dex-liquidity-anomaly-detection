# プロジェクトサービス
module "project_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.0"

  project_id = var.project_id
  activate_apis = [
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
  ]
}

# VPC アクセスコネクタ
resource "google_vpc_access_connector" "serverless" {
  project       = var.project_id
  name          = "serverless-conn"
  region        = var.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
}

# Artifact Registry
module "artifact_registry" {
  source  = "GoogleCloudPlatform/artifact-registry/google"
  version = "~> 0.3"

  project_id    = var.project_id
  location      = var.region
  format        = "DOCKER"
  repository_id = "portfolio-docker-${var.env}" # env=dev|prod
}

# Snowflake のユーザ名を Secret Manager から取得
data "google_secret_manager_secret_version" "snowflake_user" {
  project = var.project_id
  secret  = "snowflake-user"
  version = "latest"
}

# Snowflake のパスワードを Secret Manager から取得
data "google_secret_manager_secret_version" "snowflake_pass" {
  project = var.project_id
  secret  = "snowflake-pass"
  version = "latest"
}

# BentoML API
module "cloud_run_bento" {
  source         = "../../modules/cloud_run"
  project_id     = var.project_id
  name           = "bento-api-${var.env}"
  location       = var.region
  image          = "asia-northeast1-docker.pkg.dev/${var.project_id}/portfolio-docker-${var.env}/bento:latest"
  vpc_connector  = google_vpc_access_connector.serverless.id
  container_port = 3000

  depends_on = [
    module.artifact_registry
  ]

  env_vars = {
    MLFLOW_TRACKING_URI = "http://mlflow:5000"
  }
}

# Streamlit ダッシュボード
module "cloud_run_streamlit" {
  source         = "../../modules/cloud_run"
  project_id     = var.project_id
  name           = "streamlit-${var.env}"
  location       = var.region
  image          = "asia-northeast1-docker.pkg.dev/${var.project_id}/portfolio-docker-${var.env}/streamlit:${var.image_tag}"
  container_port = 8501

  vpc_connector = google_vpc_access_connector.serverless.id

  env_vars = {
    BENTO_API_URL      = "https://bento-api-${var.env}-${var.region}.run.app/predict"
    SNOWFLAKE_USER     = data.google_secret_manager_secret_version.snowflake_user.secret_data
    SNOWFLAKE_PASSWORD = data.google_secret_manager_secret_version.snowflake_pass.secret_data
  }

  depends_on = [
    module.artifact_registry,
    module.cloud_run_bento,
  ]
}

# MLflow
module "cloud_run_mlflow" {
  source         = "../../modules/cloud_run"
  project_id     = var.project_id
  name           = "mlflow-${var.env}"
  location       = var.region
  image          = "asia-northeast1-docker.pkg.dev/${var.project_id}/portfolio-docker-${var.env}/mlflow:${var.image_tag}"
  container_port = 5000

  vpc_connector = google_vpc_access_connector.serverless.id

  env_vars = {
    ARTIFACT_ROOT        = "gs://${var.artifacts_bucket}/mlflow-artifacts"
    BACKEND_DATABASE_URL = "postgresql://user:pass@host:5432/mlflow"
  }

  depends_on = [
    module.artifact_registry,
  ]
}
