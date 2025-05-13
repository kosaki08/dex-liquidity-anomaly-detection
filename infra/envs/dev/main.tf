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

resource "google_vpc_access_connector" "serverless" {
  project       = var.project_id
  name          = "serverless-conn"
  region        = var.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
}

module "artifact_registry" {
  source  = "GoogleCloudPlatform/artifact-registry/google"
  version = "~> 0.3"

  project_id    = var.project_id
  location      = var.region
  format        = "DOCKER"
  repository_id = "portfolio-docker-${var.env}" # env=dev|prod
}

module "cloud_run_bento" {
  source         = "../../modules/cloud_run"
  project_id     = var.project_id
  name           = "bento-api-${var.env}"
  location       = var.region
  image          = "asia-northeast1-docker.pkg.dev/${var.project_id}/portfolio-docker-${var.env}/bento:latest"
  vpc_connector  = google_vpc_access_connector.serverless.id
  container_port = 3000


  env_vars = {
    MLFLOW_TRACKING_URI = "http://mlflow:5000"
  }
}

