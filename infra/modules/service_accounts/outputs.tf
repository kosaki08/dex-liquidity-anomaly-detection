output "emails" {
  # { "bento" = "...@iam.gserviceaccount.com", … }
  value = { for k, sa in google_service_account.this : k => sa.email }
}
