output "network_name" {
  description = "作成した VPC ネットワークの名前"
  value       = google_compute_network.vpc.name
}

output "subnetwork_name" {
  description = "作成したサブネットの名前"
  value       = google_compute_subnetwork.private.name
}

output "subnetwork_self_link" {
  description = "作成したサブネットの self_link"
  value       = google_compute_subnetwork.private.self_link
}

output "network_self_link" {
  description = "作成した VPC ネットワークの self_link"
  value       = google_compute_network.vpc.self_link
}

output "connector_id" {
  description = "Serverless VPC Access Connector の ID"
  value       = google_vpc_access_connector.connector.id
}
