terraform {
  backend "gcs" {
    bucket = "terraform-state-portfolio-dex"
    prefix = "dex-liquidity"
  }

  required_version = ">= 1.8"
}
