from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import datetime
import random
from django.contrib.auth.models import User
import subprocess

from django.contrib.gis.db import models as gisModels

# Rendering Map Locations
from lelantos.settings import CONVERT_COORDS_FOR_MAP, folium_colours # see convert_3857_to_4326
import folium

# from folium.plugins import MarkerCluster
# from lelantos_base.models import Session, Location, Credential_Result, Device_Instance
from osgeo import ogr, osr

MAX_SESSION_ID=9223372036854775807
TIME_FORMAT="%m/%d/%Y-%H:%M:%S"

# General session for a user which can contain multiple locations & module sessions
class Session(models.Model):
    session_id = models.PositiveIntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    src_ip = models.CharField(max_length=15)
    active = models.BooleanField()
    
    def older_than_x_days(self, x_days):
        return self.start_time <= timezone.now() - datetime.timedelta(days=x_days)
    
    def older_than_one_day(self):
        return self.older_than_x_days(1)
    
    def __str__(self):
        time_formated=self.start_time.strftime(TIME_FORMAT)
        return f"Session ({self.session_id}) started at {time_formated}, from src_ip: {self.src_ip}"
    
    def getMostRecentLocation(self):
        return self.location_set.first()
    
class Location(gisModels.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    name = gisModels.CharField(max_length=100)
    location = gisModels.PointField()
    area = gisModels.CharField(max_length=100)
    remarks = gisModels.CharField(max_length=1000)
    convert_coords_for_map=CONVERT_COORDS_FOR_MAP # see convert_3857_to_4326
    uniqueIdentifiers=() # to conform with analysis functions
    
    def convert_3857_to_4326 (self, coords_3857):
        """
        There is a bug (slightly documented online) in using spatiaLite on a kali OS.
        OSMWidget, and db saving coordinates are coerced into srid: 3857, rather than the 
        alledged django default srid: 4326. After a lot of research it does not seem to 
        be fixable natively
        
        Instead using osgeo a manual conversion can be done to convert to 4326 for map visualisation  
        
        Adapted from 
        https://stackoverflow.com/questions/69084910/why-does-print-show-srid-3847-in-geodjango/69211700
        #69211700
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
    
    def addLocToMap(self, mapAddObj, colour_idx, popupStr="", icon="user", prefix="fa"):
        """Adds a location Model to map with colour index from foliums allowed colors"""
        if popupStr == "":
            popupStr = f'{self.area} ({self.remarks})'
        # For each location get all module sessions relating to this location
        if self.convert_coords_for_map:
            x, y = self.convert_3857_to_4326([self.location[0], self.location[1]])
        else:
            x, y = self.location[0], self.location[1]
        folium.Marker(
            location=(x,y),
            tooltip=self.name,
            popup=popupStr,
            icon=folium.Icon(color=folium_colours[colour_idx], icon='user', prefix=prefix)
        ).add_to(mapAddObj)
        
    # Some functions to satisfy the model-result interface allowing 
    # convenient function re-use in template rendering
    @classmethod
    def addModelsAtLocToMap(self, mapAddObj, loc, colour_idx):
        """To satisfy analysis interface for convenient plotting integration"""
        loc.addLocToMap(mapAddObj, colour_idx)
    
    @classmethod
    def getAllModelsFromUserAndUniqueSet(self, user):
        """To satisfy analysis interface for convenient plotting integration"""
        return None, None, None
    
    @classmethod
    def getModelUniqueIdentifierPatternString(self):
        return ""

"""
    Allows tracking of arbitrary linux processes for modules
    Also allows ending process through model method
"""
    
class Module_Session(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    module_name = models.CharField(max_length=2000)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    active = models.BooleanField()
    pid = models.PositiveIntegerField(null=True)
    
    def end_module_session(self):
        ended = subprocess.run(["sudo", "kill", "-9", str(self.pid)]).returncode == 0
        self.end_time=timezone.now()
        self.active=False
        self.save()
        return ended
    
# Meta Class to use for analysis, mapping and networking
# Interface design in this manner also any model which inherits this model class
# to be visualised and analysed directly, and accessile from API endpoints
class Model_Result_Instance(models.Model):
    class Meta:
        abstract=True
    
    # All model results will have a module session associated
    module_session_captured=models.ForeignKey(Module_Session, on_delete=models.CASCADE)
    
    # to filter 'instances' into unqiue sets
    uniqueIdentifiers=()
    modelType=None
    
    @classmethod
    def get_subclasses(cls):
        """Finds all subclasses of this model for automatic UI population"""
        content_types = ContentType.objects.filter(app_label=cls._meta.app_label)
        models = [ct.model_class() for ct in content_types]
        return [model for model in models
                if (model is not None and
                    issubclass(model, cls) and
                    model is not cls)]
    
    @classmethod
    def getModelUniqueIdentifierPatternString(self):
        """Help string for the pattern that defines a unique 'result' """
        return "__".join(self.uniqueIdentifiers)
        
    @classmethod
    def getAllModelsFromUserAndUniqueSet(self, user):
        """
        User to pass in context to template parsing Gets all model instances associated with user
            Finds unique set within these models on uniqueIdentifiers
        returns QuerySet, UniqueModelDicts
        """
        # Get all instances for user
        allCredInstances = self.objects.filter(module_session_captured__session__user=user)
        # get unique set
        uniqueCreds = allCredInstances.values(*self.uniqueIdentifiers).distinct()
        return allCredInstances, uniqueCreds, self.uniqueIdentifiers
        
    # = = = = = = = = = = = = = = = = Methods for analysis = = = = = = = = = = = = = = = = = = = = =
    # - - - - - - - - - - - - - - - - Plotting Models on Map - - - - - - - - - - - - - - - - - - - -
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # - - - - - - - - - - - - - Mapping All Models - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def addModelsAtLocToMap(self, mapAddObj, loc, colour_idx):
        """
        For a location adds any model instances captured here to map 
        with colour index from foliums allowed colors
        """
        modelsString=""
        for model in self.objects.filter(module_session_captured__location=loc):
            modelsString += f"{model.getMsgFromModel()}\n"
        # Add marker if not nil
        if modelsString != "":
            loc.addLocToMap(mapAddObj, colour_idx, popupStr=modelsString)
        return modelsString
    
    # - - - - - - - - - - - - - Mapping single model - - - - - - - - - - - - - - - - - - - - -
    def addThisInstanceToMap(self, mapAddObj, colour_idx):
        """
        Adds this specific model instance to map with colour index from foliums allowed colors
        pop-up will be location details
        """
        loc = self.module_session_captured.location
        loc.addLocToMap(mapAddObj, colour_idx)
    
    def getMsgFromModel(self):
        """Message to display on pop-up at a location, can be overwritten, defaults to nodes value"""
        return f"({self.getNodeString()})"
    
    # - - - - - - - - - Handingly a specific result request - - - - - - - - - - - - - - - - -
    @classmethod    
    def unpackSpecificModelRequest(self, request):
        "Unpacks request parameters to display a specific model instance on map"
        paramDict={}
        paramDictCleaned={}
        # unpack request
        for paramKey in self.uniqueIdentifiers:
            paramVal = request.GET.get(paramKey, None)
            paramDict[paramKey]=paramVal
        
        # remove None values
        for key, value in paramDict.items():
            if value is not None:
                paramDictCleaned[key]=value
        
        # validate
        if len(paramDictCleaned) == 0:
            None, f"invalid req parameters, none of {self.uniqueIdentifiers} specified"
        return paramDictCleaned, None 
        
    @classmethod 
    def parseSpecificModelParamRequest(self, user, paramDict):
        """
        Uses params dictionary to filter model results for desired hits
        Constructs a message to display filter in readble format on webpage
        Constructs request parameter string to cluster/uncluster this specific request
        """
        # get all credential entrys for this result based on parameters
        reqParams=[]
        messageBase=f"{self._meta.model_name} locations for:"
        filterQuerySet = self.objects.filter(module_session_captured__session__user=user)
        results=filterQuerySet.filter(**paramDict)
        
        # Get request url params for template
        for key, val in paramDict.items():
            reqParams.append(f"{key}={val}")
        displayMsg=messageBase+",".join([f" {keypair}" for keypair in reqParams])
        reqParamString="&".join(reqParams)
        return results, displayMsg, reqParamString  

    
    # - - - - - - - - - - - - - - - - - - Network Graphs  - - - - - - - - - - - - - - - - - - - - - -
    # Node String Conversions from model instance - - - - - - - - - - - - - - - - - - - - - - - - - -
    # In order to create network diagrams model 'instances' (location-specific) need converted into 
    # 'unique' sets i.e. nodes (location-agnostic) in order to connect 'uniqie' entries based on location
    # these functions identify 'nodes' based on models uniqueIdentifiers  
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def getNodeString(self):
        """
        Takes this model instance returns the unique node string for that model
        node string will <uniqueID1Value>:<uniqueID2Value>:...
        """
        return self.getNodeIdentifierFromDict(self.__dict__)

    @classmethod 
    def getNodeIdentifierFromDict(self, instanceDict):
        """
        Takes a dictionary representation of model and returns the unique node string for that model
        node string will <uniqueID1Value>:<uniqueID2Value>:...
        """
        uniqueElems=[instanceDict[uniqueID] for uniqueID in self.uniqueIdentifiers]
        return "__".join(uniqueElems)
    
    @classmethod 
    def getModelDictFromNodeString(self, nodeString):
        """Gets device dictionary from node identifier"""
        uniqueIdValues=nodeString.split("__")
        modelDict={}
        for uniqueID, uniqueIDValue in zip(self.uniqueIdentifiers, uniqueIdValues):
            modelDict[uniqueID]=uniqueIDValue
        return modelDict
    
    # Generating Network Elements (nodes and edges) - - - - - - - - - - - - - - - - - - - - - - - - -
    # With the ability to identify unique 'nodes' from the above functions, this functions
    # gather all nodes (based on speific model type), and edges (where multiple nodes present at
    # the same location) to be displayed on a network graph
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def getNodesFromUser(self, user):
        """
        Gets all unique nodes for model type using uniqueIdentifiers defined for the model
        """
        # get unique set 'nodes'
        _, uniqueSets, _ = self.getAllModelsFromUserAndUniqueSet(user)
        # add node for each unique set
        nodes=[self.getNodeIdentifierFromDict(dict) for dict in uniqueSets]
        return nodes
    
    @classmethod
    def getNodeEdgesByLocationFromUser(self, user):
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
                modelQS=list(self.objects.filter(module_session_captured__location=loc))
                # Check if multiple credentials captured
                if len(modelQS)>1:
                    # loop through QS until penultimate element (as ultimate element will be paired in subloop)
                    for outerIndex, fromModel in enumerate(modelQS[:-1]):
                        fromNode=fromModel.getNodeString()
                        # loop through elemenets after current to add pair
                        for toModel in modelQS[outerIndex+1:]:
                            toNode=toModel.getNodeString()
                            edges.append([fromNode,toNode])
                            # add to list of nodes with edges
                            if fromNode not in nodesWithEdges:
                                nodesWithEdges.append(fromNode)
                            if toNode not in nodesWithEdges:
                                nodesWithEdges.append(toNode)
        return edges, nodesWithEdges
    # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
    
# It's an 'instance' because mac addresses, and ip constantly change. 
# By storing it in memory data analytic techniques can be used 
# to interrogate device patterns And begin wider assoications
class Device_Instance(Model_Result_Instance):
    mac_addr=models.CharField(max_length=200)
    ip=models.CharField(max_length=200)
    private_ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)
    first_seen=models.CharField(max_length=200)
    
    # All that needs defined to use the inherited netowrk 
    # plotting functions are the model's unique identifiers 
    # which determine 'nodes'
    uniqueIdentifiers=('mac_addr', 'type')

# Credential result relating to a device instance
class Credential_Result(Model_Result_Instance):
    device=models.ForeignKey(Device_Instance, on_delete=models.CASCADE)
    ip=models.CharField(max_length=200)
    type=models.CharField(max_length=200)
    username=models.CharField(max_length=200)
    password=models.CharField(max_length=200)
    capture_time=models.CharField(max_length=200)
    
    # All that needs defined to use the inherited netowrk plotting functions
    # are the model's unique identifiers which determine 'nodes'
    uniqueIdentifiers=('username', 'password')

# Uncomment to demo IMSI capturing mock data
class Demo_IMSI_Result(Model_Result_Instance):
    sdr_settings=models.CharField(max_length=200)
    imsi=models.CharField(max_length=200)
    uniqueIdentifiers=('imsi',)


# // Deprecated - useful if wifipumpkin improve kali distro
class Wp3_Authentication_Token(models.Model):
    # TODO - move session to Wp3RestSession
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
    token = models.CharField(max_length=2000)
    issued_at = models.DateTimeField()
    
    def __str__(self):
        partial_token=self.token[0:5]
        time_formated=self.issued_at.strftime(TIME_FORMAT)
        return f"token ({partial_token}*...*) for session {self.session.session_id}, issued at {time_formated}"

class User_Action(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    placeholder = models.CharField(max_length=2000)
    time_stamp = models.DateTimeField()
    
    def __str__(self):
        time_formated=self.time_stamp.strftime(TIME_FORMAT)
        return f"{self.placeholder} at {time_formated}"
    
# Utils
def get_new_valid_session_id()->int:
    activeIds=[s.session_id for s in Session.objects.all()]
    trial_id=random.randint(1,MAX_SESSION_ID)
    while trial_id in activeIds:
        trial_id+=1
        trial_id%=MAX_SESSION_ID
    return trial_id
    

