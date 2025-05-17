# ローカル変数
locals {
  # secret_id × email の組み合わせを平坦化
  bindings = flatten([
    for secret_id, emails in var.accessors : [
      for email in emails : {
        secret_id = secret_id
        email     = email
      }
    ]
  ])
}

# Secret に対して accessor 権限を付与
resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = {
    for b in local.bindings :
    "${b.secret_id}-${b.email}" => b
  }

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.email}"
}
