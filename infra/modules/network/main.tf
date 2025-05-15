# 1) VPC ネットワーク作成
resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# 2) プライマリリージョンサブネット追加
resource "google_compute_subnetwork" "private" {
  project                  = var.project_id
  name                     = "${var.network_name}-subnet"
  ip_cidr_range            = var.subnet_ip_cidr_range
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true # Secret Manager など Private Google APIs に到達するため設定
}

# 3) Serverless VPC Access Connector
resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = var.vpc_connector_name
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_ip_cidr_range
}

# 4) インターネットへのアウトバウンドを許可
resource "google_compute_firewall" "allow_egress_internet" {
  name    = "${var.network_name}-egress"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "EGRESS"
  allow {
    protocol = "all"
  }
  destination_ranges = ["0.0.0.0/0"]
  priority           = 65534
}
