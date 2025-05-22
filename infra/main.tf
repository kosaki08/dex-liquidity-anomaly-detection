locals {
  env = terraform.workspace
}

# プロジェクトサービス
module "project_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.0"

  project_id = local.project_id
}

# VPC ネットワーク
module "network" {
  source                  = "./modules/network"
  project_id              = local.project_id
  region                  = local.region
  network_name            = "dex-network-${local.env}"
  vpc_connector_name      = "serverless-conn-${local.env}"
  subnet_ip_cidr_range    = "10.9.0.0/24"
  connector_ip_cidr_range = "10.8.0.0/28"

  depends_on = [
    google_project_service.enabled["compute.googleapis.com"]
  ]
}

# サービスアカウント
module "service_accounts" {
  source     = "./modules/service_accounts"
  project_id = local.project_id
  sa_names   = ["bento", "streamlit", "airflow"]
  env        = local.env

  depends_on = [
    google_project_service.enabled["iamcredentials.googleapis.com"]
  ]
}

# Secret モジュール
module "secrets" {
  source     = "./modules/secrets"
  project_id = local.project_id

  accessors = {
    # Streamlit SA へ認証情報の accessor を付与
    "snowflake-pass"      = [module.service_accounts.emails["streamlit"]]
    "snowflake-user"      = [module.service_accounts.emails["streamlit"]]
    "snowflake-account"   = [module.service_accounts.emails["streamlit"]]
    "snowflake-warehouse" = [module.service_accounts.emails["streamlit"]]
    "snowflake-database"  = [module.service_accounts.emails["streamlit"]]
    "snowflake-schema"    = [module.service_accounts.emails["streamlit"]]
    "snowflake-role"      = [module.service_accounts.emails["streamlit"]]

    # Bento SA へ mlflow-token の accessor を付与
    "mlflow-token" = [module.service_accounts.emails["bento"]]
  }

  depends_on = [
    google_project_service.enabled["secretmanager.googleapis.com"]
  ]
}

# Artifact Registry
module "artifact_registry" {
  source  = "GoogleCloudPlatform/artifact-registry/google"
  version = "~> 0.3"

  project_id    = local.project_id
  location      = local.region
  format        = "DOCKER"
  repository_id = "portfolio-docker-${local.env}" # dev|prod

  depends_on = [
    google_project_service.enabled["artifactregistry.googleapis.com"]
  ]
}

# BentoML API
module "cloud_run_bento" {
  source                = "./modules/cloud_run"
  project_id            = local.project_id
  name                  = "bento-api-${local.env}"
  location              = local.region
  image                 = "asia-northeast1-docker.pkg.dev/${local.project_id}/portfolio-docker-${local.env}/bento:latest"
  vpc_connector         = module.network.connector_id
  container_port        = 3000
  service_account_email = module.service_accounts.emails["bento"]

  env_vars = {
    MLFLOW_TRACKING_URI = module.cloud_run_mlflow.url
  }

  secret_env_vars = {
    MLFLOW_TOKEN = {
      secret  = "mlflow-token"
      version = "latest"
    }
  }

  depends_on = [
    google_project_service.enabled["run.googleapis.com"],
    module.artifact_registry,
    module.secrets
  ]
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
  vpc_connector = null

  # サービスアカウントを指定
  service_account_email = module.service_accounts.emails["streamlit"]

  env_vars = {
    BENTO_API_URL = "${module.cloud_run_bento.url}/predict"
  }

  secret_env_vars = {
    SNOWFLAKE_PASSWORD  = { secret = "snowflake-pass", version = "latest" }
    SNOWFLAKE_USER      = { secret = "snowflake-user", version = "latest" }
    SNOWFLAKE_ACCOUNT   = { secret = "snowflake-account", version = "latest" }
    SNOWFLAKE_WAREHOUSE = { secret = "snowflake-warehouse", version = "latest" }
    SNOWFLAKE_DATABASE  = { secret = "snowflake-database", version = "latest" }
    SNOWFLAKE_SCHEMA    = { secret = "snowflake-schema", version = "latest" }
    SNOWFLAKE_ROLE      = { secret = "snowflake-role", version = "latest" }
  }

  depends_on = [
    module.artifact_registry,
    module.secrets
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
  memory         = "1Gi"

  vpc_connector = null

  env_vars = {
    ARTIFACT_ROOT        = "gs://${local.artifacts_bucket}/mlflow-artifacts"
    BACKEND_DATABASE_URL = "postgresql://user:pass@host:5432/mlflow"
  }

  depends_on = [
    module.artifact_registry,
  ]
}

# Composer
resource "google_composer_environment" "composer" {
  provider = google-beta
  name     = "dex-airflow-${terraform.workspace}" # dex-airflow-dev / dex-airflow-prod
  project  = local.project_id
  region   = local.region # asia-northeast1

  config {
    # ネットワーク設定
    node_config {
      network         = module.network.network_self_link
      subnetwork      = module.network.subnetwork_self_link
      service_account = google_service_account.composer.email
    }

    # ソフトウェア設定
    software_config {
      image_version = var.composer_version

      # DAG で参照する環境変数
      env_variables = {
        MLFLOW_TRACKING_URI = module.cloud_run_mlflow.url
      }

      # 追加 PyPI パッケージ
      pypi_packages = {
        "apache-airflow-providers-snowflake" = "~=5.3"
        "dbt-core"                           = "~=1.9"
        "dbt-snowflake"                      = "~=1.9"
        "mlflow"                             = "~=2.22"
        "bentoml"                            = "~=1.4"
      }
    }
  }

  depends_on = [
    google_project_service.enabled["composer.googleapis.com"],
    google_project_service.enabled["compute.googleapis.com"], # VPC / GCE 下回り
    google_project_service.enabled["run.googleapis.com"],     # DAG から Cloud Run 呼び出し許可 (invoker設定)
    google_project_iam_member.composer_sa_worker_role,
    google_project_iam_member.composer_run_invoker
  ]
}
