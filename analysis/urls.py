from django.urls import path

from . import views

urlpatterns = [
    # Home (locations)
    path("analysis_home/", views.analysis_home, name="analysis_home"),
    path("apiv1/analysis_home/", views.analysis_home_api, name="analysis_home_api"),
    
    # Results (mapped)
    path("analysis_by_model/", views.analysis_of_all_a_model_results, name="analysis_by_model"),
    path("apiv1/analysis_by_model/", views.analysis_of_all_a_model_results_api, name="analysis_by_model_api"),
    path("analysis_by_specific_model_result/", views.analysis_of_a_specific_model_result, name="analysis_by_specific_model_result"),
    path("apiv1/analysis_by_specific_model_result/", views.analysis_of_a_specific_model_result_api, name="analysis_by_specific_model_result_api"),   
    
    # Results (networked)
    path("modelNetwork/", views.model_network, name="model_network"),
    path("apiv1/modelNetwork/", views.model_network_api, name="model_network_api"),
    
]