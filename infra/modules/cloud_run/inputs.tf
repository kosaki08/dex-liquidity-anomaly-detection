variable "secret_env_vars" {
  description = "Map<string, object> for secret environment variables"
  type = map(object({
    secret  = string
    version = string
  }))
  default = {}
}
