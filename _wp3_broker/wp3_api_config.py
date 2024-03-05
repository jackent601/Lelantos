# API Basics
WP3_API_USERNAME="test"
WP3_API_PASSWORD="test"
WP3_API_IP="127.0.0.1"
WP3_API_PORT=1337
WP3_API_SERVER_ADDRESS="http://127.0.0.1:1337"
WP3_API_CONNECT_TIMEOUT="10.0"

# Auth Token
WP3_API_TOKEN_EXTENSION="/api/v1/authenticate/"

# AP Config
WP3_API_AP_CONFIG_EXTENSION="/api/v1/config/accesspoint"

# lower case to use in django to avoid confusion of settings file
WP3_API_DEFAULT_CONFIG_MAP={
    "wp3_api_ip": WP3_API_IP,
    "wp3_api_port": WP3_API_PORT,
    "wp3_server_address": WP3_API_SERVER_ADDRESS,
    "wp3_api_username": WP3_API_USERNAME,
    "wp3_api_password": WP3_API_PASSWORD,
    "wp3_api_connect_timeout": WP3_API_CONNECT_TIMEOUT,
    "wp3_api_token_extension": WP3_API_TOKEN_EXTENSION,
    "wp3_api_ap_config_extension": WP3_API_AP_CONFIG_EXTENSION,
}

# Aux
WP3_SERVER_START_WAIT_TIME=3