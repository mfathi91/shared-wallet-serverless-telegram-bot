variable "json_config" {
  type      = string
  sensitive = true
}

variable "username1" {
  type = string
}

variable "username2" {
  type = string
}

variable "gemini_api_key" {
  type      = string
  sensitive = true
  default   = ""
}