from django.shortcuts import render, redirect
from django.contrib import messages

import portal_auth.utils as auth_utils  

# Rendering Map Locations
from wp3_portal.settings import DEFAULT_LOCATION_SETTINGS 
import folium
from folium.plugins import MarkerCluster
from wp3_basic.models import Session, Location, Credential_Result, Device_Instance, Model_Result_Instance
from osgeo import ogr, osr
from wp3_portal.settings import folium_colours

# Network Graphs
import networkx as nx
import plotly.graph_objs as go
import plotly

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# URLS
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def analysis_by_model_type(request, template, modelType):
    """
    Displays all model instances of specified type captured, by location, coloured by session for a user on a map
    Provides unique Models as context for template rendering
    """
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # get instance to access methods
    mInstance = modelType()
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
    
    # Plot Markers that have credential results
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            mInstance.addModelsAtLocToMap(mapAddObj, loc, colour_idx)
        # increment color to color by session
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    # Get unique models to display in table for filter
    _, uniqueModelsDictsOnly, uniqueFieldIdentifiers = mInstance.getAllModelsFromUserAndUniqueSet(active_session.user)
    
    # Get the total filter for each model
    uniqueModels=[]
    if uniqueModelsDictsOnly is not None:
        for modelDict in uniqueModelsDictsOnly:
            totalFilterReq = "&".join([f"{key}={val}" for key, val in modelDict.items()])
            uniqueModels.append({"modelDict":modelDict, "modelTotalFilterReq":totalFilterReq})
    
    return render(request, template, 
                  {'map': m._repr_html_(), 
                   'clustered':clustered, 
                   'uniqueFieldIdentifiers': uniqueFieldIdentifiers,
                   'uniqueModels':uniqueModels})

def analysis_by_specific_model_instance(request, template, modelType):
    """Displays all locations a specific model result is captured for a user on a map"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # get instance to access methods
    mInstance = modelType()
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
        
    # unpack specific model request & validate
    paramsReqDict, errMsg = mInstance.unpackSpecificModelRequest(request)
    if errMsg is not None:
        message=messages.error(request, errMsg)
        return redirect('analysis_home')  

    # Use request params to parse QuerySet, display message, and request string
    filterQuerySet, displayMsg, reqParamString = mInstance.parseSpecificModelParamRequest(active_session.user, paramsReqDict)
    
    # Add location for each instance
    for modelEntry in filterQuerySet:
        modelEntry.addThisInstanceToMap(mapAddObj, 0)
    
    # Get unique models to display in table for filter
    _, uniqueModelsDictsOnly, uniqueFieldIdentifiers = mInstance.getAllModelsFromUserAndUniqueSet(active_session.user)
    
    # Get the total filter for each model
    uniqueModels=[]
    for modelDict in uniqueModelsDictsOnly:
        totalFilterReq = "&".join([f"{key}={val}" for key, val in modelDict.items()])
        print(totalFilterReq)
        uniqueModels.append({"modelDict":modelDict, "modelTotalFilterReq":totalFilterReq})
    
    return render(request, 
                  template, 
                  {'map': m._repr_html_(), 
                   'clustered':clustered,
                   'reqParamString':reqParamString, 
                   'displayMsg':displayMsg, 
                   'uniqueFieldIdentifiers': uniqueFieldIdentifiers,
                   'uniqueModels':uniqueModels})

from django.apps import apps
def analysis_home(request):
    """Displays all locations coloured by session for a user on a map"""
    subclasses = Model_Result_Instance.get_subclasses()
    Invoice = apps.get_model(app_label=subclasses[0]._meta.app_label, model_name=subclasses[0]._meta.model_name)
    print(Invoice)
    return analysis_by_model_type(request, template="analysis/analysis.html", modelType=Location)

def analysis_by_creds(request):
    """Displays all credentials captured at a location, coloured by session for a user on a map"""
    return analysis_by_model_type(request, template="analysis/analysis_by_creds.html", modelType=Credential_Result)

def analysis_by_specific_cred(request):
    """Displays all locations a specific credential result is captured for a user on a map"""
    return analysis_by_specific_model_instance(request, template="analysis/analysis_by_specific_creds.html", modelType=Credential_Result)
    
def analysis_by_dev(request):
    """Displays all devices captured at a location, coloured by session for a user on a map"""
    return analysis_by_model_type(request, template="analysis/analysis_by_devices.html", modelType=Device_Instance)

def analysis_by_specific_dev(request):
    """Displays all locations a specific device result is captured for a user on a map"""
    # Get all model result subclasses
    return analysis_by_specific_model_instance(request, template="analysis/analysis_by_specific_dev.html", modelType=Device_Instance)  
    
def modelNetwork(request, 
                 modelType,
                 template, 
                 minNodeSize=30, 
                 maxNodeSize=70):
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
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Nodes (credentials) - - - - - - - - - - - - - - - 
    m = modelType() # get instance to access methods
    nodes=m.getNodesFromUser(user=active_session.user)

    # Edges (credential co-located)  - - - - - - - - -
    edges, nodesWithEdges = m.getNodeEdgesByLocationFromUser(user=active_session.user)
              
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
    NodesWithNoEdges=[m.getModelDictFromNodeString(c) for c in nodesWithNoEdges]
    NodesWithEdges=[m.getModelDictFromNodeString(c) for c in nodesWithEdges]
    
    return render(request, template, 
                  {'networkGraph':networkGraph, 
                   'nodesWithNoEdges':NodesWithNoEdges,
                   'nodesWithEdges':NodesWithEdges})
    
def credentialNetwork(request):
    """
    Creates a network graph for credential results based on results captured at the same location
    As networked by location:
        Each node represents a unique credential result (agnostic of location)
        Each edge represents where a both credential results are present at the same location
        
    Nodes are scaled in colour and size based on connectivity
        
    It does the node/edge creation first to omit any credentials not networked from graph for a clean
    output and displays these in a separate table instead 
    """
    return modelNetwork(request, Credential_Result, "analysis/credentialNetwork.html")
    
def deviceNetwork(request):
    """
    Creates a network graph for device results based on results captured at the same location
    
    WARNING: mac_addr:type assumed to be unique identifier however with rotating mac address 
    security protocols this is not true hence this if POC only
    
    As networked by location:
        Each node represents a unique device result (agnostic of location)
        Each edge represents where a both device results are present at the same location
        
    Nodes are scaled in colour and size based on connectivity
        
    It does the node/edge creation first to omit any credentials not networked from graph for a clean
    output and displays these in a separate table instead 
    """
    return modelNetwork(request, 
                         Device_Instance,
                        "analysis/deviceNetwork.html")


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# Utils
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# - - - - - - - - - - - - Map Utils - - - - - - - - - - - - - - - -
def getMap(request):
    """Creates folium map to render with optional clustering based on request params"""
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    mapAddObj = m
    
    # optional clustering
    clustered=False
    clusterMarkers = request.GET.get('clusterMarkers', None)
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