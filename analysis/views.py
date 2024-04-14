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

def analysis_home(request):
    """Displays all locations coloured by session for a user on a map"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
        
    # Get All Sessions for this user
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            addLocToMap(mapAddObj, loc, colour_idx)
        # increment color to color by session
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    return render(request, "analysis/analysis.html", {'map': m._repr_html_(), 'clustered':clustered})

def analysis_by_creds(request):
    """Displays all credentials captured at a location, coloured by session for a user on a map"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
    
    # Plot Markers that have credential results
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            # Add all credential results captured at this location to map marker
            addCredsAtLocToMap(mapAddObj, loc, colour_idx)
        # increment color to color by session
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    # Get unique credentials to display in table for filter
    _, uniqueCreds = getAllCredsFromUser(active_session.user)
    
    return render(request, "analysis/analysis_by_creds.html", 
                  {'map': m._repr_html_(), 
                   'clustered':clustered, 
                   'uniqueCreds':uniqueCreds})

def analysis_by_specific_cred(request):
    """Displays all locations a specific credential result is captured for a user on a map"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
        
    # unpack specific cred
    cType, cUsername, cPassword, _redirect = unpackSpecificCredRequest(request)
    if _redirect is not None:
        return _redirect

    # Use request params to parse QuerySet, display message, and request string
    credFilterQuerySet, credMsg, reqParamString = parseCredentialParamRequest(active_session.user, cType, cUsername, cPassword)
    
    # Add location for each instance this credentil was found
    for credEntry in credFilterQuerySet:
        addLocToMap(mapAddObj, credEntry.module_session_captured.location, 0)
        
    # Get unique credentials to display in table for filter
    _, uniqueCreds = getAllCredsFromUser(active_session.user)
    
    return render(request, "analysis/analysis_by_specific_creds.html", 
                  {'map': m._repr_html_(), 
                   'clustered':clustered,
                   'reqParamString':reqParamString, 
                   'credMsg':credMsg,
                   'uniqueCreds':uniqueCreds})
    
def analysis_by_dev(request):
    """Displays all devices captured at a location, coloured by session for a user on a map"""
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Get Map
    m, mapAddObj, clustered = getMap(request)
    
    # Plot Markers that have credential results
    colour_idx = 0
    for sesh in Session.objects.filter(user=active_session.user):
        # Get all locations for each session
        for loc in Location.objects.filter(session=sesh):
            # Add all credential results captured at this location to map marker
            addDeviceAtLocToMap(mapAddObj, loc, colour_idx)
        # increment color to color by session
        colour_idx=(colour_idx+1)%len(folium_colours)
    
    # Get unique credentials to display in table for filter
    _, uniqueDevices = getAllDevicesFromUser(active_session.user)
    
    return render(request, "analysis/analysis_by_devices.html", 
                  {'map': m._repr_html_(), 
                   'clustered':clustered, 
                   'devices':uniqueDevices})
    
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
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Nodes (credentials) - - - - - - - - - - - - - - - 
    allCredNodes=getCredNodesForUser(active_session.user)

    # Edges (credential co-located)  - - - - - - - - -
    credEdges, credNodesWithEdges = getCredNodeEdgesForUser(active_session.user)
              
    # Remove nodes with no connections
    credNodesWithNoEdges=[]
    for c in allCredNodes:
        if c not in credNodesWithEdges:
            credNodesWithNoEdges.append(c)
    
    # Get network figure
    fig = getScaledNetworkGraph(credNodesWithEdges, credEdges, 70, 30)

    # prepare plot for django rendering
    networkGraph=plotly.offline.plot(fig, auto_open = False, output_type="div")
    
    # get credential details for each table
    credNodesWithNoEdges=[getCredDictFromNodeString(c) for c in credNodesWithNoEdges]
    credNodesWithEdges=[getCredDictFromNodeString(c) for c in credNodesWithEdges]
    
    return render(request, "analysis/credentialNetwork.html", 
                  {'networkGraph':networkGraph, 
                   'nodesWithNoEdges':credNodesWithNoEdges,
                   'nodesWithEdges':credNodesWithEdges})
    

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
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    
    # Nodes (credentials) - - - - - - - - - - - - - - - 
    allDeviceNodes=getDeviceNodesForUser(active_session.user)

    # Edges (credential co-located)  - - - - - - - - -
    deviceEdges, devicesWithEdges = getDeviceNodeEdgesForUser(active_session.user)
              
    # Remove nodes with no connections
    deviceNodesWithNoEdges=[]
    for d in allDeviceNodes:
        if d not in devicesWithEdges:
            deviceNodesWithNoEdges.append(d)
    
    # Get network figure
    fig = getScaledNetworkGraph(devicesWithEdges, deviceEdges, 70, 30)

    # prepare plot for django rendering
    networkGraph=plotly.offline.plot(fig, auto_open = False, output_type="div")
    
    # get credential details for each table
    deviceNodesWithNoEdges=[getDevDictFromNodeString(c) for c in deviceNodesWithNoEdges]
    devicesWithEdges=[getDevDictFromNodeString(c) for c in devicesWithEdges]
    
    return render(request, "analysis/deviceNetwork.html", 
                  {'networkGraph':networkGraph, 
                   'nodesWithNoEdges':deviceNodesWithNoEdges,
                   'nodesWithEdges':devicesWithEdges})
    

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# Utils
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

# - - - - - - - - - - - - - Map Utils - - - - - - - - - - - - - - - -
# General
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

def addLocToMap(mapAddObj, loc, colour_idx):
    """Adds a location Model to map with colour index from foliums allowed colors"""
    popupStr = f'{loc.area} ({loc.remarks})'
    # For each location get all module sessions relating to this location
    x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
    folium.Marker(
        location=(x,y),
        tooltip=loc.name,
        popup=popupStr,
        icon=folium.Icon(color=folium_colours[colour_idx], icon='user')
    ).add_to(mapAddObj)

# Credential   
def getCredMsgString(cred):
    """Gets a credential string to label location marker with for display"""
    if cred.type == "wifi-password":
        return f"({cred.type};{cred.password})"
    else:
        return f"({cred.type};{cred.username};{cred.password})"
    
def addCredsAtLocToMap(mapAddObj, loc, colour_idx):
    """For a location adds any credential results captured to map with colour index from foliums allowed colors"""
    return addModelAtLocToMap(mapAddObj, loc, Credential_Result, getCredMsgString, colour_idx)

# Device
def addDeviceAtLocToMap(mapAddObj, loc, colour_idx):
    """For a location adds any device instance seen to map with colour index from foliums allowed colors"""
    return addModelAtLocToMap(mapAddObj, loc, Device_Instance, getNodeStringFromDevice, colour_idx)
    
def addModelAtLocToMap(mapAddObj, loc, model, getMsgFromModel, colour_idx):
    """For a location adds any credential results captured to map with colour index from foliums allowed colors"""
    modelsString=""
    modelsAdded=0
    for model in model.objects.filter(module_session_captured__location=loc):
        modelsString += f"{getMsgFromModel(model)}\n"
        modelsAdded+=1
    # Add marker if not nil
    if modelsString != "":
        print(loc.location) # debug
        popupStr = f'{loc.area} ({loc.remarks})'
        # For each location get all module sessions relating to this location
        x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
        folium.Marker(
            location=(x,y),
            tooltip=loc.name,
            popup=modelsString,
            icon=folium.Icon(color=folium_colours[colour_idx], icon='user')
        ).add_to(mapAddObj)
    return modelsString

# - - - - - - - - - - - - - Cred Utils - - - - - - - - - - - - - - - - -
def unpackSpecificCredRequest(request):
    "Unpacks parameters from specific credential request"
    cType = request.GET.get('type', None)
    cUsername = request.GET.get('username', None)
    cPassword = request.GET.get('password', None)
    if cPassword is None and cUsername is None and cType is None:
        message=messages.error(request, "invalid cred parameters, none of type, username or password specified")
        return None, None, None, redirect('analysis_by_creds')
    return cType, cUsername, cPassword, None  
    
def getAllCredsFromUser(user):
    """Gets all credntial results captured by a user"""
    allCredInstances = Credential_Result.objects.filter(module_session_captured__session__user=user)
    # get unique set
    uniqueCreds = allCredInstances.values('type', 'username', 'password').distinct()
    return allCredInstances, uniqueCreds

def parseCredentialParamRequest(user, cType, cUsername, cPassword):
    """
    Uses params to filter credential results for desired hits
    Constructs a message to display filter in readble format on webpage
    Constructs request parameter string to cluster/uncluster this specific request
    """
    # get all credential entrys for this result based on parameters
    reqParams=[]
    credMessageBase="Credential Locations for:"
    credMessageElements=[]
    credFilterQuerySet = Credential_Result.objects.filter(module_session_captured__session__user=user)
    if cType is not None:
        credFilterQuerySet=credFilterQuerySet.filter(type=cType) 
        credMessageElements.append(f" type={cType}")
        reqParams.append(f"type={cType}")
    if cUsername is not None:
        credFilterQuerySet=credFilterQuerySet.filter(username=cUsername) 
        credMessageElements.append(f" username={cUsername}")
        reqParams.append(f"username={cUsername}")
    if cPassword is not None:
        credFilterQuerySet=credFilterQuerySet.filter(password=cPassword)
        credMessageElements.append(f" password={cPassword}")
        reqParams.append(f"password={cPassword}")
    credMsg=credMessageBase+",".join(credMessageElements)
    reqParamString="&".join(reqParams)
    return credFilterQuerySet, credMsg, reqParamString 

# - - - - - - - - - - - - Device Utils - - - - - - - - - - - - - - - - -
def getAllDevicesFromUser(user):
    """Gets all device instance results captured by a user"""
    allDeviceInstances = Device_Instance.objects.filter(module_session_captured__session__user=user)
    # get unique set
    uniqueDevices = allDeviceInstances.values('mac_addr', 'type').distinct()
    return allDeviceInstances, uniqueDevices

def parseDeviceParamRequest(user, dMac, dType):
    """
    Uses params to filter device results for desired hits
    Constructs a message to display filter in readble format on webpage
    Constructs request parameter string to cluster/uncluster this specific request
    """
    # get all credential entrys for this result based on parameters
    reqParams=[]
    devMessageBase="Device Locations for:"
    deviceMessageElements=[]
    deviceFilterQuerySet = Device_Instance.objects.filter(module_session_captured__session__user=user)
    if dMac is not None:
        deviceFilterQuerySet=deviceFilterQuerySet.filter(mac_addr=dMac) 
        deviceMessageElements.append(f" mac_addr={dMac}")
        reqParams.append(f"mac_addr={dMac}")
    if dType is not None:
        deviceFilterQuerySet=deviceFilterQuerySet.filter(type=dType) 
        deviceMessageElements.append(f" type={dType}")
        reqParams.append(f"type={dType}")
    deviceMsg=devMessageBase+",".join(deviceMessageElements)
    reqParamString="&".join(reqParams)
    return deviceFilterQuerySet, deviceMsg, reqParamString 

# - - - - - - - - - - - Network Utils - - - - - - - - - - - - - - - -
# General
def getNodesFromQuerySet(QuerySet, nodeIdentifierFromDict, *identifiers):
    """
    Gets all unique nodes from a django query set
        QuerySet: django query set to generate nodes from
        nodeIdentifierFromDict: function to generate unique node string as identifier
        *identifiers: django model identifiers which define uniqueness 
    """
    # get unique set 'nodes'
    uniqueSets = QuerySet.values(*identifiers).distinct()
    # add node for each unique set
    nodes=[]
    for dict in uniqueSets:
        nodeString=nodeIdentifierFromDict(dict)
        nodes.append(nodeString)
    return nodes

def getNodeEdgesByLocation(user, model, getNodeStringFromModel):
    """
    Gets all edges (co-located model entries) for a user (using double looping with moving index for each location)
        user: user
        model: django model used to identify edges at location
        getNodeStringFromModel: function to get unique node string from model
    """
    # loop through locations for user
    nodesWithEdges=[]
    edges=[]
    for sesh in Session.objects.filter(user=user):
        for loc in Location.objects.filter(session=sesh):
            # get credentials captured at this location
            modelQS=list(model.objects.filter(module_session_captured__location=loc))
            # Check if multiple credentials captured
            if len(modelQS)>1:
                # loop through QS until penultimate element (as ultimate element will be paired in subloop)
                for outerIndex, fromModel in enumerate(modelQS[:-1]):
                    fromNode=getNodeStringFromModel(fromModel)
                    # loop through elemenets after current to add pair
                    for toModel in modelQS[outerIndex+1:]:
                        toNode=getNodeStringFromModel(toModel)
                        edges.append([fromNode,toNode])
                        # add to list of nodes with edges
                        if fromNode not in nodesWithEdges:
                            nodesWithEdges.append(fromNode)
                        if toNode not in nodesWithEdges:
                            nodesWithEdges.append(toNode)
    return edges, nodesWithEdges

# Credential
def getNodeStringFromCredential(cred):
    """Gets node identifier string for network graph from django model"""
    return f"{cred.username}:{cred.password}"

def getNodeStringFromCredDict(credDict):
    """Gets node identifier string for network graph from credential dictionary"""
    uName=credDict['username']
    pswd=credDict['password']
    return f"{uName}:{pswd}"

def getCredDictFromNodeString(nodeString):
    """Gets credential dictionary from node identifier"""
    elements=nodeString.split(":")
    return {"username":elements[0], "password":elements[1]}

def getCredNodesForUser(user):
    """Gets all unique nodes (credential identifiers) captured by a user"""
    # Get all credentials captured by this user
    credsFromUser = Credential_Result.objects.filter(module_session_captured__session__user=user)
    return getNodesFromQuerySet(credsFromUser, getNodeStringFromCredDict, 'username', 'password')

def getCredNodeEdgesForUser(user):
    """Gets all edges (co-located credentials) for a user"""
    return getNodeEdgesByLocation(user, Credential_Result, getNodeStringFromCredential)

# Device
def getNodeStringFromDevice(dev):
    """Gets device node identifier string for network graph from django model"""
    return f"{dev.mac_addr}:{dev.type}"

def getNodeStringFromDeviceDict(devDict):
    """Gets device node identifier string for network graph from device dictionary"""
    mac=devDict['mac_addr']
    t=devDict['type']
    return f"{mac}:{t}"

def getDevDictFromNodeString(nodeString):
    """Gets device dictionary from node identifier"""
    elements=nodeString.split(":")
    return {"mac_addr":elements[0], "type":elements[1]}

def getDeviceNodesForUser(user):
    """Gets all unique nodes (credential identifiers) captured by a user"""
    # Get all credentials captured by this user
    devicesFromUser = Device_Instance.objects.filter(module_session_captured__session__user=user)
    return getNodesFromQuerySet(devicesFromUser, getNodeStringFromDeviceDict, 'mac_addr', 'type')

def getDeviceNodeEdgesForUser(user):
    """Gets all edges (co-located credentials) for a user"""
    return getNodeEdgesByLocation(user, Device_Instance, getNodeStringFromDevice)

# Graph
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