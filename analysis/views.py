from django.shortcuts import render, redirect
from django.contrib import messages
from django.apps import apps
from django.http import HttpResponse

# For API
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict
import json

import portal_auth.utils as auth_utils  

# Rendering Map Locations
from lelantos.settings import DEFAULT_LOCATION_SETTINGS 
import folium
from folium.plugins import MarkerCluster
from lelantos_base.models import Session, Location, Model_Result_Instance
from lelantos.settings import folium_colours

# Network Graphs
import networkx as nx
import plotly.graph_objs as go
import plotly

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# URLS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# - - - - - - - - - - - - - - Utils - - - - - - - - - - - - - - - - - 
def getContextFromRequestAndValidate(request):
    """
    Retrieves all values needed for all template rendering. 
    Including Model type & Validation
    """
    # Display Context
    displayContext={}
    
    # unpack model params to get specific model
    app_label = request.GET.get('app_label', None)
    model_name = request.GET.get('model_name', None)
    if app_label is None or model_name is None:
        message=messages.error(request, "app_label and model_name must be provided parameters to view model_results")
        return None, None, redirect('analysis_home') 
    pageParamReq=f"app_label={app_label}&model_name={model_name}" 
    
    # Load to context
    displayContext['app_label']=app_label 
    displayContext['model_name']=model_name 
    displayContext['modelParamReq']=pageParamReq
    
    # cluster markers
    displayContext['clusterMarkers'] = request.GET.get('clusterMarkers', None)
    
    # Get model type from params
    modelType = apps.get_model(app_label=displayContext['app_label'], model_name=displayContext['model_name'])
    displayContext['uniqueIdentifierPattern']=modelType.getModelUniqueIdentifierPatternString()
    displayContext['uniqueFieldIdentifiers']=modelType.uniqueIdentifiers
    
    # Get subclasses available for detailed analysis to autogenerate buttons
    subclasses = Model_Result_Instance.get_subclasses()
    subclassesNames=[{
        'model_name':subclass._meta.model_name,
        'app_label':subclass._meta.app_label} 
                     for subclass in subclasses]
    displayContext['modelResultOptions']=subclassesNames
    return modelType, displayContext, None 

# - - - - - - - - - - - - - - MAPS - - - - - - - - - - - - - - - - - -
# Base Wrapper For Mapping Results (or Locations as a specific case)
def analysis_by_model_results(request, 
                              template="analysis/analysis_by_model_results.html",
                              specificResult=False):
    """
    Reuseable function for all base models (results and locations)
    
    Displays all model instances of specified type captured, by location, coloured by session for a user on a map
    Parameters used to find model type in order to rendered required data
    As all model results inherit from the same class any model created as a subclass of Model_Result_Instance can
    automatically be rendered in this manner
    
    Locations only is a special case of this function rendering with a template override
    """
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect, None
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home'), None
    
    # Display Context
    modelType, displayContext, _redirect=getContextFromRequestAndValidate(request)
    if _redirect is not None:
        return _redirect, None
    
    # results (for api)
    displayContext['allResults']=[]
    
    # Get Map
    m, mapAddObj, clustered = getMap(displayContext['clusterMarkers'])
    displayContext['clustered']=clustered
    
    # Switch on whether mapping specific result, or all results
    if specificResult:
        # Switch on whether GET (view result instance) or POST (view where two nodes co-located)
        if request.method=="GET":
            # unpack specific model request & validate
            paramsReqDict, errMsg = modelType.unpackSpecificModelRequest(request)
            if errMsg is not None:
                message=messages.error(request, errMsg)
                return redirect('analysis_home'), None

            # Use request params to parse QuerySet, display message, and request string
            filterQuerySet, displayMsg, reqParamString = modelType.parseSpecificModelParamRequest(active_session.user, paramsReqDict)
            displayContext['modelParamReq']+=f"&{reqParamString}"
            displayContext['map_title']=displayMsg
            
            # Add location for each instance
            _allResults=[]
            for modelEntry in filterQuerySet:
                modelEntry.addThisInstanceToMap(mapAddObj, 0)
                loc=modelEntry.module_session_captured.location
                # Get API construct by coercing geo data and adding to result
                _mod=model_to_dict(modelEntry)
                _mod['location']={"loc_id":loc.id, "location": loc.location.wkt, "name":loc.name, "area":loc.area, "remarks":loc.remarks}
                _allResults.append(_mod)
            displayContext['allResults']=_allResults
        else:
            pS = request.POST
            # Get all locations of node1
            node1 = request.POST.get('node1', None)
            node1Dict = modelType.getModelDictFromNodeString(node1)
            node1Instances = modelType.objects.filter(**node1Dict)
            node1Locations = [n1Instance.module_session_captured.location for n1Instance in node1Instances]
            
            node2 = request.POST.get('node2', None)
            node2Dict = modelType.getModelDictFromNodeString(node2)
            node2Instances = modelType.objects.filter(**node2Dict)
            
            # colocated instances
            coLocations=[]
            for n2Instance in node2Instances:
                if n2Instance.module_session_captured.location in node1Locations:
                    coLocations.append(n2Instance.module_session_captured.location)
                    
            # add to map
            _allResults=[]
            for loc in coLocations:
                modelType.addModelsAtLocToMap(mapAddObj, loc, 0)
                # for api
                _allResults.append({"node1":node1,
                                    "node2":node2,
                                    "loc_id":loc.id, 
                                    "location": loc.location.wkt, 
                                    "name":loc.name, "area":loc.area, 
                                    "remarks":loc.remarks})
            displayContext['allResults']=_allResults
            
            # for webpage
            displayContext['map_title']=f"Co-locations of '{node1}' and '{node2}'"
            displayContext['disableClustering']='disabled'     
    else:
        # Plot Markers that have model results
        colour_idx = 0
        displayContext['map_title']=f"Locations where {displayContext['model_name']}s were captured"
        _models=[]
        for sesh in Session.objects.filter(user=active_session.user):
            # Get all locations for each session
            for loc in Location.objects.filter(session=sesh):
                modelType.addModelsAtLocToMap(mapAddObj, loc, colour_idx)
                
                # Get API construct by coercing geo data and adding to result
                if modelType._meta.model_name == Location._meta.model_name:
                    # catch case where model is location
                    _models.append({"loc_id":loc.id, "location": loc.location.wkt, "name":loc.name, "area":loc.area, "remarks":loc.remarks})
                else:
                    # otherwise add all model results at this location
                    for mod in modelType.objects.filter(module_session_captured__location=loc):
                        _mod=model_to_dict(mod)
                        _mod['location']={"loc_id":loc.id, "location": loc.location.wkt, "name":loc.name, "area":loc.area, "remarks":loc.remarks}
                        _models.append(_mod)
                    
            # increment color to color by session
            colour_idx=(colour_idx+1)%len(folium_colours)
        # for api only
        displayContext['allResults']=_models
    
    # Get unique models to display in table for filter
    _, uniqueModelsDictsOnly, _ = modelType.getAllModelsFromUserAndUniqueSet(active_session.user)
    
    # Get the total filter for each model to populate results table
    uniqueModels=[]
    if uniqueModelsDictsOnly is not None:
        for modelDict in uniqueModelsDictsOnly:
            totalFilterReq = "&".join([f"{key}={val}" for key, val in modelDict.items()])
            uniqueModels.append({"modelDict":modelDict, "modelTotalFilterReq":totalFilterReq})
    
    # Load remaining context
    displayContext['results_title']=f"All {displayContext['model_name']}s"
    displayContext['map']=m._repr_html_()
    displayContext['uniqueModels']=uniqueModels
    # displayContext['allModels']=allModels
    
    # render this model type
    return render(request, template, displayContext), displayContext 

# Individual URLs to handle wrapper
def analysis_home(request):
    """
    Displays all locations coloured by session for a user on a map
    location implements the required interface so can be rendered as a 'model result' in itself
    so set the request parameters and render with a template override
    """
    request.GET._mutable = True
    request.GET['app_label']=Location._meta.app_label
    request.GET['model_name']=Location._meta.model_name
    homeWebPage, _ = analysis_by_model_results(request, template="analysis/analysis_home.html")
    return homeWebPage

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analysis_home_api(request):
    """
    API of analysis_home results
    """
    request.GET._mutable = True
    request.GET['app_label']=Location._meta.app_label
    request.GET['model_name']=Location._meta.model_name
    _, ctx = analysis_by_model_results(request, template="analysis/analysis_home.html")
    return renderAPIContext(ctx, geoData=True)

def analysis_of_all_a_model_results(request):
    """Displays all results relating to a model type (type found by request parameters)""" 
    resultsWebPage, _ = analysis_by_model_results(request, specificResult=False)
    return resultsWebPage

def analysis_of_a_specific_model_result(request):
    """Displays all results relating to a specific model instance (instance found by request parameters)""" 
    resultsWebPage, _ = analysis_by_model_results(request, specificResult=True)
    return resultsWebPage

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def analysis_of_all_a_model_results_api(request):
    """API of Displays analysis_of_all_a_model_results results""" 
    _, ctx = analysis_by_model_results(request)
    return renderAPIContext(ctx)

@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def analysis_of_a_specific_model_result_api(request):
    """API of Displays analysis_of_a_specific_model_result results """ 
    _, ctx = analysis_by_model_results(request, specificResult=True)
    # dont need unique models when calling specific one
    del ctx['uniqueModels']
    return renderAPIContext(ctx)
     
# - - - - - - - - - - - Network Graphs (from co-locations) - - - - - - - - - - - - - - - - - -
# Base Wrapper For Networking Results
def model_network_context(request,template="analysis/modelNetwork.html",minNodeSize=30,maxNodeSize=70):
    """
    Creates a network graph for a Django module, provided model has a module_session foreign key
    As networked by location:
        Each node represents a unique django model entry result (agnostic of location)
            unique defined by list of identifiers passed in 
        Each edge represents where both unique models are present at the same location
        
    Renders the template with context of:
        NodesWithEdges: created by parsing each connected node string with getModelDictFromNodeString
        NodesWithNoEdges: created by parsing each non-connected node string with getModelDictFromNodeString
    
    Nodes are scaled in colour and size based on connectivity
        
    It does the node/edge creation first to omit any model instances not networked from graph for a clean
    output and displays these in a separate table instead 
    """
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect, None
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home'), None
    
    # Display Context
    modelType, displayContext, _redirect=getContextFromRequestAndValidate(request)
    if _redirect is not None:
        return _redirect, None
    
    # Nodes (credentials) - - - - - - - - - - - - - - - 
    # m = modelType() # get instance to access methods
    nodes=modelType.getNodesFromUser(user=active_session.user)
    displayContext['allNodes']=nodes

    # Edges (credential co-located)  - - - - - - - - -
    edges, nodesWithEdges = modelType.getNodeEdgesByLocationFromUser(user=active_session.user)
              
    # Remove nodes with no connections
    nodesWithNoEdges=[]
    for c in nodes:
        if c not in nodesWithEdges:
            nodesWithNoEdges.append(c)
    
    # Get network figure
    fig = getScaledNetworkGraph(nodesWithEdges, edges, maxNodeSize, minNodeSize)

    # prepare plot for django rendering
    networkGraph=plotly.offline.plot(fig, auto_open = False, output_type="div")
    
    # get credential details for each table
    NodesWithNoEdges=[modelType.getModelDictFromNodeString(c) for c in nodesWithNoEdges]
    NodesWithEdges=[modelType.getModelDictFromNodeString(c) for c in nodesWithEdges]
    
    # display text
    map_title=f"{displayContext['model_name']}s networked by co-location"
    map_sub_title=f"\"{modelType.getModelUniqueIdentifierPatternString()}\" assumed to uniquely identifier a {displayContext['model_name']}"
    
    # Get the total filter for each model to populate results table
    NodesWithEdgesForDisplay=[]
    for nodeDict in NodesWithEdges:
        totalFilterReq = "&".join([f"{key}={val}" for key, val in nodeDict.items()])
        NodesWithEdgesForDisplay.append({"modelDict":nodeDict, "modelTotalFilterReq":totalFilterReq})
    NodesWithNoEdgesForDisplay=[]
    for nodeDict in NodesWithNoEdges:
        totalFilterReq = "&".join([f"{key}={val}" for key, val in nodeDict.items()])
        NodesWithNoEdgesForDisplay.append({"modelDict":nodeDict, "modelTotalFilterReq":totalFilterReq})
        
    # Load remaining context
    displayContext['map']=networkGraph
    displayContext['map_title']=map_title
    displayContext['disableClustering']='disabled'
    displayContext['map_sub_title']=map_sub_title
    displayContext['nodesWithEdges']=NodesWithEdgesForDisplay
    displayContext['nodesWithNoEdges']=NodesWithNoEdgesForDisplay
    displayContext['edges']=edges
        
    return render(request, template, displayContext), displayContext

def model_network(request, template="analysis/modelNetwork.html", minNodeSize=30, maxNodeSize=70):
    """model network rendering"""
    networkWebPage, _ = model_network_context(request, template, minNodeSize, maxNodeSize)
    return networkWebPage

@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def model_network_api(request, template="analysis/modelNetwork.html", minNodeSize=30, maxNodeSize=70):
    """model network api"""
    _, ctx = model_network_context(request, template, minNodeSize, maxNodeSize)
    return renderAPIContext(ctx, network=True)
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# Utils
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# - - - - - - - - - - - - Map Utils - - - - - - - - - - - - - - - -
def getMap(clusterMarkers):
    """Creates folium map to render with optional clustering based on request params"""
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    mapAddObj = m
    
    # optional clustering
    clustered=False
    if clusterMarkers is not None:
        mapAddObj = MarkerCluster().add_to(m)
        clustered=True
    return m, mapAddObj, clustered

# - - - - - - - - - - - - Network Utils - - - - - - - - - - - - - - - -
def getScaledNetworkGraph(nodes, edges, maxNodeSize, minNodeSize):
    """Creates a network graph for nodes and edges and scales/colours nodes based on connectivity"""
    #Create a blank graph page

    G = nx.Graph()
    
    # Add only connected nodes
    for n in nodes:
        G.add_node(n)
    
    # Add edges of connected nodes:
    for e in edges:
        G.add_edge(e[0], e[1])
        
    # Generate positions    
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Map to network graph
    for n, p in pos.items():
        G.nodes[n]['pos'] = p
        
    # PLOTLY
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)
        
    # PLOTLY
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)
        
    node_adjacencies = []
    node_text = []
    for node, adjacencies in enumerate(G.adjacency()):
        node_adjacencies.append(len(adjacencies[1]))
        node_text.append(f'{adjacencies[0]}, '+str(len(adjacencies[1]))+' connections')
    
    # prep node sizes by scaling as appropriate
    maxAdjacency=max(node_adjacencies)
    minAdjacency=min(node_adjacencies)
    relativeAdjacencies=[(a-minAdjacency)/(maxAdjacency-minAdjacency) for a in node_adjacencies]
    scaledSize=[minNodeSize+(maxNodeSize-minNodeSize)*relA for relA in relativeAdjacencies]
        
    # format nodes
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            colorscale='Viridis',
            reversescale=True,
            color=[],
            size=scaledSize,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line_width=2))
    
    # colour and label markers
    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text
        
    # create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    return fig

# - - - - - - - - - - - - - - API Utils - - - - - - - - - - - - - - - - - -
def renderAPIContext(ctx, network=False, geoData=False):
    # remove fields not needed in api
    del ctx['map']
    del ctx['clusterMarkers']
    if network:
        del ctx['disableClustering']
        del ctx['map_sub_title']
    else:
        del ctx['clustered']
        del ctx['results_title']
    del ctx['modelResultOptions']
    del ctx['map_title']
    # # construct api response
    apiResponse=json.dumps(ctx)
    return HttpResponse(apiResponse, content_type="application/json")
    # return HttpResponse(ctx['allModels'], content_type="application/json")