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
  log_config {
    aggregation_interval = "INTERVAL_5_MIN"       # ログ集計間隔5分ごと
    flow_sampling        = 0.5                    # サンプリング率50%
    metadata             = "INCLUDE_ALL_METADATA" # メタデータを含める
  }
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
# tfsec:ignore:google-compute-no-public-egress # GCP Private Google Access 向けのため許容
resource "google_compute_firewall" "allow_egress_internet" {
  name    = "${var.network_name}-egress"
  project = var.project_id
  network = google_compute_network.vpc.name

  direction = "EGRESS"
  allow {
    protocol = "all"
  }

  # プライベートGoogleアクセスアドレスのみが許可しているため、　tfsec　の警告を　ignore
  destination_ranges = ["199.36.153.4/30"] # GCP Private Google Access 範囲
  priority           = 65534
}
