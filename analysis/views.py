from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User

import portal_auth.utils as auth_utils  

# Rendering Map Locations
from wp3_portal.settings import DEFAULT_LOCATION_SETTINGS 
import folium
from folium.plugins import MarkerCluster
from wp3_basic.models import Session, Location, Credential_Result, Device_Instance
from osgeo import ogr, osr

# Network
import networkx as nx
import plotly.graph_objs as go
import plotly

def convert_3857_to_4326 (coords_3857):
    """
    There is a bug (slightly documented) in using spatiaLite, OSMWidget, and db saving in that coordinates
    are coerced into srid: 3857, rather than the alledged django default srid: 4326. After a lot of research
    for the above combintation it does not seem to be fixable natively!!
    
    Instead using osgeo a manual conversion can be done to convert to 4326 for map visualisation  
    
    Adapted from https://stackoverflow.com/questions/69084910/why-does-print-show-srid-3847-in-geodjango/69211700#69211700
    """
    # create Geometry Object
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(coords_3857[0], coords_3857[1])
    
    # create coordinate transformation
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(3857)
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)

    coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    # transform point
    point.Transform(coordTransform)

    return point.GetX(),  point.GetY() 

folium_colours = ["red", 
                  "blue",
                  "green",
                  "purple",
                  "orange",
                  "darkred",
                  "lightred",
                  "beige",
                  "darkblue",
                  "darkgreen",
                  "cadetblue",
                  "darkpurple",
                  "white",
                  "pink",
                  "lightblue",
                  "lightgreen",
                  "gray",
                  "black",
                  "lightgray"]

# Create your views here.
def analysis_home(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    mapAddObj = m
    
    # optional clustering
    clustered=False
    clusterMarkers = request.GET.get('clusterMarkers', None)
    if clusterMarkers is not None:
        marker_cluster = MarkerCluster().add_to(m)
        mapAddObj = marker_cluster
        clustered=True
        
    
    # Get All Sessions for this user
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            print(loc.location) # debug
            popupStr = f'{loc.area} ({loc.remarks})'
            # For each location get all module sessions relating to this location
            x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
            folium.Marker(
                location=(x,y),
                tooltip=loc.name,
                popup=popupStr,
                icon=folium.Icon(color=folium_colours[colour_idx], icon='user')
            ).add_to(mapAddObj)
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    return render(request, "analysis/analysis.html", {'map': m._repr_html_(), 'clustered':clustered})

def analysis_by_creds(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    mapAddObj = m
    
    # optional clustering
    clustered=False
    clusterMarkers = request.GET.get('clusterMarkers', None)
    if clusterMarkers is not None:
        marker_cluster = MarkerCluster().add_to(m)
        mapAddObj = marker_cluster
        clustered=True
    
    # Plot Markers that have credential results
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            # Get all credential results captured at this location
            creds=""
            for cred in Credential_Result.objects.filter(module_session_captured__location=loc):
                creds += f"{getCredString(cred)}\n"
            # Add marker if not nil
            if creds != "":
                print(loc.location) # debug
                popupStr = f'{loc.area} ({loc.remarks})'
                # For each location get all module sessions relating to this location
                x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
                folium.Marker(
                    location=(x,y),
                    tooltip=loc.name,
                    popup=creds,
                    icon=folium.Icon(color=folium_colours[colour_idx], icon='user')
                ).add_to(mapAddObj)
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    # Get unique credentials
    # first get all credentials captured by this user
    credsFromUser = Credential_Result.objects.filter(module_session_captured__session__user=active_session.user)
    # get unique set
    uniqueCreds = credsFromUser.values('type', 'username', 'password').distinct()
    
    
    return render(request, "analysis/analysis_by_creds.html", {'map': m._repr_html_(), 'clustered':clustered, 'uniqueCreds':uniqueCreds})

def analysis_by_specific_cred(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    mapAddObj = m
    
    # optional clustering
    clustered=False
    clusterMarkers = request.GET.get('clusterMarkers', None)
    if clusterMarkers is not None:
        marker_cluster = MarkerCluster().add_to(m)
        mapAddObj = marker_cluster
        clustered=True
        
    # unpack specific cred
    cType = request.GET.get('type', None)
    cUsername = request.GET.get('username', None)
    cPassword = request.GET.get('password', None)
    if cPassword is None and cUsername is None and cType is None:
        message=messages.error(request, "invalid cred parameters, none of type, username or password specified")
        return redirect('analysis_by_creds')    
    
    # get all credential entrys for this result basde on parameters
    credMessageBase="Credential Locations for:"
    credMessageElements=[]
    credsFromUser = Credential_Result.objects.filter(module_session_captured__session__user=active_session.user)
    if cType is not None:
        credsFromUser=credsFromUser.filter(type=cType) 
        credMessageElements.append(f" type={cType}")
    if cUsername is not None:
        credsFromUser=credsFromUser.filter(username=cUsername) 
        credMessageElements.append(f" username={cUsername}")
    if cPassword is not None:
        credsFromUser=credsFromUser.filter(password=cPassword)
        credMessageElements.append(f" password={cPassword}")
    credMsg=credMessageBase+",".join(credMessageElements)
    
    # get all locations from these results
    for credEntry in credsFromUser:
        loc = credEntry.module_session_captured.location
        # Add location
        # For each location get all module sessions relating to this location
        x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
        popupStr = f'{loc.area} ({loc.remarks})'
        folium.Marker(
            location=(x,y),
            tooltip=loc.name,
            popup=popupStr,
            icon=folium.Icon(icon='user')
        ).add_to(mapAddObj)
        
    # Get unique credentials
    # first get all credentials captured by this user
    credsFromUser = Credential_Result.objects.filter(module_session_captured__session__user=active_session.user)
    # get unique set
    uniqueCreds = credsFromUser.values('type', 'username', 'password').distinct()
    
    return render(request, "analysis/analysis_by_specific_creds.html", 
                  {'map': m._repr_html_(), 
                   'clustered':clustered, 
                   'credMsg':credMsg,
                   'uniqueCreds':uniqueCreds})
    
def network(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    #Create a blank graph page
    G = nx.Graph()
    
    # Nodes (credentials) - - - - - - - - - - - - - - - 
    # Get all credentials captured by this user
    credsFromUser = Credential_Result.objects.filter(module_session_captured__session__user=active_session.user)
    # get unique set 'nodes'
    uniqueCredsDicts = credsFromUser.values('username', 'password').distinct()
    # add node for each credential
    allCredNodes=[]
    for credDict in uniqueCredsDicts:
        nodeString=getCredDictNodeString(credDict)
        allCredNodes.append(nodeString)

    # Nodes & Edges (credential co-located)  - - - - - - - - -
    # loop through locations for user
    credNodesWithEdges=[]
    credEdges=[]
    for sesh in Session.objects.filter(user=active_session.user):
        for loc in Location.objects.filter(session=sesh):
            # get credentials captured at this location
            credsAtLocation=Credential_Result.objects.filter(module_session_captured__location=loc)
            # Check if multiple credentials captured
            if len(credsAtLocation)>1:
                # add each node _pair_ by double looping with a moving index
                curIndex=0
                for fromCred in credsAtLocation:
                    fromNode=getCredNodeString(fromCred)
                    # check if final node
                    if curIndex == len(credsAtLocation)-1:
                        break
                    # add all edges for this node
                    for toCred in credsAtLocation[curIndex+1:]:
                        toNode=getCredNodeString(toCred)
                        credEdges.append([fromNode,toNode])
                        # add to list of nodes with edges
                        if fromNode not in credNodesWithEdges:
                            credNodesWithEdges.append(fromNode)
                        if toNode not in credNodesWithEdges:
                            credNodesWithEdges.append(toNode)
                        # increment index
                        curIndex+=1
                        
    # Remove nodes with no connections
    credNodesWithNoEdges=[]
    for c in allCredNodes:
        if c not in credNodesWithEdges:
            credNodesWithNoEdges.append(c)
    
    # Add only connected nodes
    for c in credNodesWithEdges:
        G.add_node(c)
    
    # Add edges of connected nodes:
    for cEdge in credEdges:
        G.add_edge(cEdge[0], cEdge[1])
        
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
    maxNodeSize=70
    minNodeSize=30
    maxAdjacency=max(node_adjacencies)
    minAdjacency=min(node_adjacencies)
    relativeAdjacencies=[(a-minAdjacency)/(maxAdjacency-minAdjacency) for a in node_adjacencies]
    scaledSize=[minNodeSize+(maxNodeSize-minNodeSize)*relA for relA in relativeAdjacencies]
        
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
            colorscale='YlGnBu',
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


    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text
        
    fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    # title='<br>AT&T network connections',
                    # titlefont=dict(size=16),
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    # annotations=[ dict(
                    #     # text="No. of connections",
                    #     showarrow=False,
                    #     xref="paper", yref="paper") ],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))

    networkGraph=plotly.offline.plot(fig, auto_open = False, output_type="div")
    credNodesWithNoEdges=[getCredDictFromNodeString(c) for c in credNodesWithNoEdges]
    credNodesWithEdges=[getCredDictFromNodeString(c) for c in credNodesWithEdges]
    return render(request, "analysis/network.html", 
                  {'networkGraph':networkGraph, 
                   'nodesWithNoEdges':credNodesWithNoEdges,
                   'nodesWithEdges':credNodesWithEdges})

# Utils
def getCredString(cred):
    if cred.type == "wifi-password":
        return f"({cred.type};{cred.password})"
    else:
        return f"({cred.type};{cred.username};{cred.password})"

def getCredNodeString(cred):
    return f"{cred.username}:{cred.password}"

def getCredDictFromNodeString(nodeString):
    elements=nodeString.split(":")
    return {"username":elements[0], "password":elements[1]}
    

def getCredDictNodeString(credDict):
    uName=credDict['username']
    pswd=credDict['password']
    return f"{uName}:{pswd}"