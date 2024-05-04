from django.test import TestCase
from lelantos_base.models import AbstractModelResultsTestClass
# from django.utils import timezone
from django.http import HttpRequest
from lelantos_base.tests.testModels import testDataPrep
from django.test import Client

# Functions to test
from analysis.views import getContextFromRequestAndValidate, renderAPIContext, analysis_by_model_results, model_network_context, getScaledNetworkGraph

def analysisPrep(cls):
    """ conventional test data and logs user in and prepares request to analysis endpoints"""
    testDataPrep(cls)
    cls.c = Client()
    cls.c.login(username=cls.user_username, password=cls.user_password)
    # Request Params (success case)
    cls.expectedAppLabel="lelantos_base"
    cls.expectedModelName="abstractmodelresultstestclass"
    cls.expectedPageParamReq=f"app_label={cls.expectedAppLabel}&model_name={cls.expectedModelName}"
    # Request (success Case)
    req=HttpRequest()
    req.GET._mutable = True
    req.GET['app_label']=cls.expectedAppLabel
    req.GET['model_name']=cls.expectedModelName
    req.user=cls.user
    cls.successBaseReq=req

class Analysis_Utils_TestCase(TestCase):
    """
    Utilities for handling general requests and fetching specific child instances from requests
    """
    @classmethod
    def setUpTestData(cls):
        print("Analysis_Utils_TestCase - - - - - - - - - - - - - - - - - - - - - - -")
        analysisPrep(cls)
    
    def test_getContextFromRequestAndValidate_Success(self):
        """ successful request to retrieve model type and context """
        # Get context
        modelType, ctx, _redirect = getContextFromRequestAndValidate(self.successBaseReq, False)
        # no error expected
        self.assertEqual(None, _redirect)
        # Check params retrieved from request ito context
        self.assertEqual(ctx['app_label'], self.expectedAppLabel)
        self.assertEqual(ctx['model_name'], self.expectedModelName)
        self.assertEqual(ctx['modelParamReq'], self.expectedPageParamReq)
        # Check correct model type
        self.assertEqual(modelType, AbstractModelResultsTestClass)
        print("     pass: test_getContextFromRequestAndValidate_Success")
        
    def test_getContextFromRequestAndValidate_Fail_NoModelName(self):
        """ failed request (no model name) to retrieve model type and context """
        # Get context
        failReq = self.successBaseReq
        failReq.GET['model_name'] = None
        _, _, _redirect = getContextFromRequestAndValidate(self.successBaseReq, False)
        # error expected
        self.assertNotEqual(None, _redirect)
        print("     pass: test_getContextFromRequestAndValidate_Fail_NoModelName")
        
    def test_getContextFromRequestAndValidate_Fail_ModelNotFound(self):
        """ failed request (model doesnt exist) to retrieve model type and context """
        # Get context
        failReq = self.successBaseReq
        failReq.GET['model_name'] = "doesntExist"
        _, _, _redirect = getContextFromRequestAndValidate(self.successBaseReq, False)
        # error expected
        self.assertNotEqual(None, _redirect)
        print("     pass: test_getContextFromRequestAndValidate_Fail_NoModelName")
        
    def test_getContextFromRequestAndValidate_Fail_NoAppLabel(self):
        """ failed request (no app label) to retrieve model type and context """
        # Get context
        failReq = self.successBaseReq
        failReq.GET['app_label'] = None
        modelType, ctx, _redirect = getContextFromRequestAndValidate(self.successBaseReq, False)
        # error expected
        self.assertNotEqual(None, _redirect)
        print("     pass: test_getContextFromRequestAndValidate_Fail_NoAppLabel")
        
    
class Analysis_API_TestCase(TestCase):
    """
    API returns json encoded results response, this tests rendering is as epected
    """
    @classmethod
    def setUpTestData(cls):
        print("Analysis_API_TestCase - - - - - - - - - - - - - - - - - - - - - - - -")
        analysisPrep(cls)
        
    def test_renderAPIContext(self):
        """ Checks the results contet is renderable into json resposne """
        # Get context (tested above)
        _, ctx, _ = getContextFromRequestAndValidate(self.successBaseReq, False)
        # Add other fields expected to be populated
        ctx['map']=""
        ctx['clusterMarkers']=""
        ctx['clustered']=""
        ctx['results_title']=""
        ctx['modelResultOptions']=""
        ctx['map_title']=""
        # Get API response
        apiResponse = renderAPIContext(ctx)
        # Expected response bytes for successful request
        expectedJsonRespBytes=b'{"app_label": "lelantos_base", "model_name": "abstractmodelresultstestclass", "modelParamReq": "app_label=lelantos_base&model_name=abstractmodelresultstestclass", "uniqueIdentifierPattern": "item__name", "uniqueFieldIdentifiers": ["item", "name"]}'
        self.assertEqual(expectedJsonRespBytes, apiResponse.content)
        print("     pass: test_renderAPIContext")

class Analysis_Results_TestCase(TestCase):
    """
    Results retrieves all models by specific requests, and associates with location data to each result
    these tests check expected models are retrieved from requests, with geo-data
    """
    @classmethod
    def setUpTestData(cls):
        print("Analysis_Results_TestCase - - - - - - - - - - - - - - - - - - - - - -")
        analysisPrep(cls)
    
    def test_analysisByModelResults_allResults(self):
        """ """
        # Get request for all model instances of type AbstractModelResultsTestClass  for this user
        _, ctx = analysis_by_model_results(self.successBaseReq)
        # Get model results from ctx
        results=ctx['allResults']
        # user has 5 results
        self.assertEqual(5, len(results))
        # 
        # Result type is garunteed fro utils tests so no need to check further
        print("     pass: analysis_by_model_results")
        
    def test_analysisByModelResults_allResults(self):
        """ All results for model type in parameters, with geo-data """
        # Get request for all model instances of type AbstractModelResultsTestClass  for this user
        _, ctx = analysis_by_model_results(self.successBaseReq)
        # Get model results from ctx
        results=ctx['allResults']
        # user has 5 results
        self.assertEqual(5, len(results))
        # check geo-data associated
        res1 = results[0]
        loc1 = res1['location']
        self.assertNotEqual(None, loc1)
        self.assertNotEqual("", loc1)
        # Result type is garunteed from utils tests so no need to check further
        print("     pass: test_analysisByModelResults_allResults")
        
    def test_analysisByModelResults_SpecificResults(self):
        """ Specific results for model instances in parameters, with geo-data """
        # Get request for specific model instances of type AbstractModelResultsTestClass for this user
        specificReq = self.successBaseReq
        specificReq.GET['item']="i1"
        specificReq.GET['name']="n1"
        specificReq.method="GET"        
        _, ctx = analysis_by_model_results(specificReq, specificResult=True)
        # Get model results from ctx
        results=ctx['allResults']
        # user has 2 instances of this node result
        self.assertEqual(2, len(results))
        # check geo-data associated
        res1 = results[0]
        loc1 = res1['location']
        self.assertNotEqual(None, loc1)
        self.assertNotEqual("", loc1)
        # Result type is garunteed from utils tests so no need to check further
        print("     pass: test_analysisByModelResults_SpecificResults")
        
    def test_analysisByModelResults_CoLocatedNodes(self):
        """ locations where two nodes are co-located """
        # Get request for co-located nodes of type AbstractModelResultsTestClass for this user
        specificReq = self.successBaseReq
        specificReq.POST['node1']="i1__n1"
        specificReq.POST['node2']="i2__n2"
        specificReq.method="POST"        
        _, ctx = analysis_by_model_results(specificReq, specificResult=True)
        # Get model results from ctx
        results=ctx['allResults']
        # 1 location where both i1__n1 and i2__n2 are present
        self.assertEqual(1, len(results))
        # check geo-data associated
        res1 = results[0]
        loc1 = res1['location']
        self.assertNotEqual(None, loc1)
        self.assertNotEqual("", loc1)
        # check node information retains
        node1 = res1['node1']
        self.assertEqual("i1__n1", node1)
        node2 = res1['node2']
        self.assertEqual("i2__n2", node2)
        print("     pass: test_analysisByModelResults_CoLocatedNodes")
        
class Analysis_Networks_TestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        print("Analysis_Networks_TestCase- - - - - - - - - - - - - - - - - - - - - -")
        analysisPrep(cls)
        
    def test_ModelNetworkContext(self):
        """ 
        Checks successful network info retrieved from request, see Lelaantos_Base.tests for
        description of expected test results
        """
        # Get Response
        resp, ctx = model_network_context(self.successBaseReq)
        # Unpack Results
        nodes=ctx['allNodes']
        edges=ctx['edges']
        nodesWithEdges=ctx['nodesWithEdges']
        nodesWithNoEdges=ctx['nodesWithNoEdges']
        # Check expected, see Lelaantos_Base.tests for description of expected test data results
        self.assertEqual(len(nodes), 4)
        self.assertEqual(len(edges), 4)
        self.assertEqual(len(nodesWithEdges), 4)
        self.assertEqual(len(nodesWithNoEdges), 0)
        for result in self.allResults:
            nodeString = result.getNodeString()
            for node in nodes:
                if node == nodeString:
                    break
            else:
                self.fail(f"{nodeString} not found in expected nodes: {nodes}")
        expectedEdges=[['i1__n1', 'i2__n2'], ['i1__n1', 'i3__n3'], ['i2__n2', 'i3__n3'],['i1__n1', 'i4__n4']]
        # check all expected edges present
        for edge in edges:
            for expectedEdge in expectedEdges:
                if edge == expectedEdge:
                    break
            else:
                self.fail(f"{edge} not found in expected edges: {expectedEdges}")
        print("     pass: test_ModelNetworkContext")
        
    def test_getScaledNetworkGraph(self):
        """ 
        Scales nodes based on relative adjacency see Lelaantos_Base.tests for expected adjacencies
        relative adjacenies calcualted here
        """
        # Get Nodes and Edges
        edges, nodesWithEdges = AbstractModelResultsTestClass.getNodeEdgesByLocationFromUser(user=self.user)
        # Get scaled sizes
        _, scaledSizes, relativeAdjacencies = getScaledNetworkGraph(nodesWithEdges, edges, 3, 1)
        # Check results
        expectedRelAdj=[1.0, 0.5, 0.5, 0.0]
        expectedScaledSizes=[3.0, 2.0, 2.0, 1.0]
        self.assertEqual(expectedRelAdj, relativeAdjacencies)
        self.assertEqual(expectedScaledSizes, scaledSizes)
        print("     pass: test_getScaledNetworkGraph")