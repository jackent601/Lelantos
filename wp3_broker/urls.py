from django.urls import path

from . import views

urlpatterns = [
    path("wp3_server_health/", views.check_wp3_api_running, name="wp3_server_health"),
    path("wp3_start_server/", views.start_wp3_rest_server, name="start_wp3_rest_server"),
    path("wp3_get_api_auth_token/", views.refresh_wp3_api_auth_token_for_session, name="wp3_get_api_auth_token"),
    path("wp3_ap_config/", views.wp3_ap_config, name="wp3_ap_config"),
    # path("wp3_wifi_scan/", views.wp3_wifi_scan, name="wp3_server_health"),
]