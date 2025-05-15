locals {
  env = terraform.workspace
}

# プロジェクトサービス
module "project_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.0"

  project_id = local.project_id
  activate_apis = [
    "cloudresourcemanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
    "iamcredentials.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

# VPC アクセスコネクタ
resource "google_vpc_access_connector" "serverless" {
  project       = local.project_id
  name          = "serverless-conn"
  region        = local.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
}

# Artifact Registry
module "artifact_registry" {
  source  = "GoogleCloudPlatform/artifact-registry/google"
  version = "~> 0.3"

  project_id    = local.project_id
  location      = local.region
  format        = "DOCKER"
  repository_id = "portfolio-docker-${local.env}" # dev|prod
}

# Snowflake のユーザ名を Secret Manager から取得
data "google_secret_manager_secret_version" "snowflake_user" {
  project = local.project_id
  secret  = "snowflake-user"
  version = "latest"
}

# Snowflake のパスワードを Secret Manager から取得
data "google_secret_manager_secret_version" "snowflake_pass" {
  project = local.project_id
  secret  = "snowflake-pass"
  version = "latest"
}

# BentoML API
module "cloud_run_bento" {
  source         = "./modules/cloud_run"
  project_id     = local.project_id
  name           = "bento-api-${local.env}"
  location       = local.region
  image          = "asia-northeast1-docker.pkg.dev/${local.project_id}/portfolio-docker-${local.env}/bento:latest"
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
  source         = "./modules/cloud_run"
  project_id     = local.project_id
  name           = "streamlit-${local.env}"
  location       = local.region
  image          = "asia-northeast1-docker.pkg.dev/${local.project_id}/portfolio-docker-${local.env}/streamlit:${var.image_tag}"
  container_port = 8501

  # VPC アクセスコネクタ
  vpc_connector = google_vpc_access_connector.serverless.id

  # サービスアカウントを指定
  service_account_email = google_service_account.streamlit.email

  env_vars = {
    BENTO_API_URL = "https://bento-api-${local.env}-${local.region}.run.app/predict"
  }

  secret_env_vars = {
    SNOWFLAKE_PASSWORD = {
      secret  = "snowflake-pass"
      version = "latest"
    }
    SNOWFLAKE_USER = {
      secret  = "snowflake-user"
      version = "latest"
    }
  }

  depends_on = [
    module.artifact_registry,
    google_secret_manager_secret_iam_member.streamlit_sa_access
  ]
}

# MLflow
module "cloud_run_mlflow" {
  source         = "./modules/cloud_run"
  project_id     = local.project_id
  name           = "mlflow-${local.env}"
  location       = local.region
  image          = "asia-northeast1-docker.pkg.dev/${local.project_id}/portfolio-docker-${local.env}/mlflow:${var.image_tag}"
  container_port = 5000

  vpc_connector = google_vpc_access_connector.serverless.id

  env_vars = {
    ARTIFACT_ROOT        = "gs://${local.artifacts_bucket}/mlflow-artifacts"
    BACKEND_DATABASE_URL = "postgresql://user:pass@host:5432/mlflow"
  }

  depends_on = [
    module.artifact_registry,
  ]
}
