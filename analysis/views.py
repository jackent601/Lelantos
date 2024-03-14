from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User

import portal_auth.utils as auth_utils  

# Rendering Map Locations
from wp3_portal.settings import DEFAULT_LOCATION_SETTINGS 
import folium
from wp3_basic.models import Location
from osgeo import ogr, osr

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

# Create your views here.
def analysis_home(request):
    # Auth
    active_session, _redirect, _error = auth_utils.get_session_from_request(request, "You must be logged in to access wifi scans")
    if _error:
        return _redirect
    if active_session is None:
        message=messages.error(request, "No active session for user, log out and in again to create a session")
        return redirect('home')
    message=messages.success(request, "Analysis!")
    
    # Get Map
    m = folium.Map(location=[DEFAULT_LOCATION_SETTINGS['default_lat'], DEFAULT_LOCATION_SETTINGS['default_lon']], zoom_start=9)
    
    # Get Capture Locations For User
    print("printing locs")
    for loc in Location.objects.filter(session__user=active_session.user):
        x, y = convert_3857_to_4326([loc.location[0], loc.location[1]])
        folium.Marker(location=(x,y)).add_to(m)
    
    return render(request, "analysis/analysis.html", {'map': m._repr_html_()})
    
