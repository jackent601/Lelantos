from django.urls import path

from . import views

urlpatterns = [
    # Home (locations)
    path("analysis_home/", views.analysis_home, name="analysis_home"),
    
    # Results (mapped)
    path("analysis_by_model/", views.analysis_of_all_a_model_results, name="analysis_by_model"),
    path("analysis_by_specific_model_result/", views.analysis_of_a_specific_model_result, name="analysis_by_specific_model_result"),
    
    # Results (networked)
    path("credentialNetwork/", views.credentialNetwork, name="credentialNetwork"),
    path("deviceNetwork/", views.deviceNetwork, name="deviceNetwork"),
]