# Secret Manager Accessor 付与
resource "google_secret_manager_secret_iam_member" "streamlit_sa_access" {
  for_each = toset([
    "snowflake-pass",
    "snowflake-user",
  ])

  project   = local.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${module.service_accounts.emails["streamlit"]}"
}
