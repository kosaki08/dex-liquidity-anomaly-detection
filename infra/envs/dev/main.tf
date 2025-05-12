module "project_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.0"

  project_id    = var.project_id
  activate_apis = [
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