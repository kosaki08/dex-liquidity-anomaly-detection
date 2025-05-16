output "network_self_link" {
  description = "作成した VPC ネットワークの self_link"
  value       = google_compute_network.vpc.self_link
}

output "connector_id" {
  description = "Serverless VPC Access Connector の ID"
  value       = google_vpc_access_connector.connector.id
}
