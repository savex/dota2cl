#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025

# This file contains constants used across the dota2cl package.
# It is a good idea to place any hardcoded values here in case they
# need to be updated in the future.
# Most of these are application defaults that can be overridden
# in the config file, see dota2cl/config.py.

app_name = "dota2cl"
# Shown in console output and used as the logger name
title = app_name

# Config file and log file names
config_file_name = app_name + ".conf"
log_file_name = app_name + ".log"
# Environment variables
# Settings are overridden with <prefix>_<SECTION>_<KEY>,
# e.g. DOTA2CL_API_THROTTLE=true
env_var_prefix = app_name.upper()
config_env_var = env_var_prefix + "_CONFIG"
opendota_api_key_env_var = "OPENDOTA_API_KEY"

log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
default_log_level = "WARNING"
default_num_teams = 5

opendota_api_base_url = "https://api.opendota.com/api"
requests_timeout_sec = 180
api_client_throttle_timeout_sec = 1
resource_cache_timeout_sec = 60  # 1 min
# Retries for 429 Too Many Requests responses
api_client_max_retries = 3
api_client_retry_backoff_sec = 2  # doubled on every retry
