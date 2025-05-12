terraform {
  backend "gcs" {
    bucket = "terraform-state-portfolio-dex"
    prefix = "prod"
  }
}
