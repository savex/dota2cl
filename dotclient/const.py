#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025

# This file contains constants used across the dotclient package.
# It is a good idea to place any hardcoded values here in case they
# need to be updated in the future.

title = "dota2client"

opendota_api_base_url = "https://api.opendota.com/api"
opendota_api_key_env_var = "OPENDOTA_API_KEY"
requests_timeout_sec = 180
api_client_throttle_timeout_sec = 1
resource_cache_timeout_sec = 60  # 1 min
# Retries for 429 Too Many Requests responses
api_client_max_retries = 3
api_client_retry_backoff_sec = 2  # doubled on every retry
