from django.test import TestCase
from django.contrib.auth.models import User
from lelantos_base.models import AbstractModelResultsTestClass, Module_Session, Location, Session
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from django.http import HttpRequest


"""
Tests location conversion is as expected
"""
class Location_TestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        print("Location_TestCase - - - - - - - - - - - - - - - - - - - - - - - - - -")
        # User
        cls.user = User.objects.create_user("test","test","test")
        # Session
        cls.sesh = Session.objects.create(session_id=1, user=cls.user, start_time=timezone.now(), src_ip="x.x.x.x", active=True)
        # Location
        testLocPoint=GEOSGeometry(f"POINT (-641025.8565339005 7308772.180542897)", srid=4326)
        cls.loc = Location.objects.create(session=cls.sesh, name="testLoc", location=testLocPoint, area="testArea", remarks="testRemarks")
        
    def test_convert_3857_to_4326(self):
        """ location conversion (see function doc-string)"""
        x, y = self.loc.convert_3857_to_4326([self.loc.location[0], self.loc.location[1]])
        # self.assertEqual(self.node1obj1.getModelUniqueIdentifierPatternString(), "item__name")
        self.assertEqual(x, 54.72549840259201)
        self.assertEqual(y, -5.758433244402104)
        print("     pass: test_convert_3857_to_4326")
"""
Tests all abstract functions required for analysis

    has 5 result entries but only 3 are unique with respect
    to unique fields, hence 5 entries -> 3 nodes
    
    location 1 has node1, 2 and 3
    location 2 has node1, and 4
    hence across all locations there are 4 edges (1,2) (1,3) (2,3) from loc1 and (1,4) from loc2
    
    As such connectivity is (node:connectivity):
        1:3
        2:2
        3:2
        4:1
"""
class Model_Result_Instance_TestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        print("Model_Result_Instance_TestCase- - - - - - - - - - - - - - - - - - - -")
        # User
        cls.user = User.objects.create_user("test","test","test")
        # Session
        cls.sesh = Session.objects.create(session_id=1, user=cls.user, start_time=timezone.now(), src_ip="x.x.x.x", active=True)
        # Location
        testLocPoint=GEOSGeometry(f"POINT (-641025.8565339005 7308772.180542897)", srid=4326)
        testLocPoint2=GEOSGeometry("POINT (-645419.0921824716 7307673.872103441)", srid=4326)
        cls.loc = Location.objects.create(session=cls.sesh, name="testLoc", location=testLocPoint, area="testArea", remarks="testRemarks")
        cls.loc2 = Location.objects.create(session=cls.sesh, name="testLoc2", location=testLocPoint2, area="testArea2", remarks="testRemarks2")
        # Module Session
        cls.mSesh= Module_Session.objects.create(session=cls.sesh, location=cls.loc, module_name="testModule", start_time=timezone.now(), active=False)
        cls.mSesh2= Module_Session.objects.create(session=cls.sesh, location=cls.loc2, module_name="testModule", start_time=timezone.now(), active=True)
        # Results
        # loc1
        cls.node1obj1 = AbstractModelResultsTestClass.objects.create(module_session_captured=cls.mSesh, name="n1", item="i1", aux="a1")
        cls.node2obj1 = AbstractModelResultsTestClass.objects.create(module_session_captured=cls.mSesh, name="n2", item="i2", aux="a2")
        cls.node3obj1 = AbstractModelResultsTestClass.objects.create(module_session_captured=cls.mSesh, name="n3", item="i3", aux="a3")
        # loc2
        cls.node1obj2 = AbstractModelResultsTestClass.objects.create(module_session_captured=cls.mSesh2, name="n1", item="i1", aux="a4")
        cls.node4obj1 = AbstractModelResultsTestClass.objects.create(module_session_captured=cls.mSesh2, name="n4", item="i4", aux="a5")
        # all results
        cls.allResults = [cls.node1obj1, cls.node2obj1, cls.node3obj1, cls.node1obj2, cls.node4obj1]

    def test_getModelUniqueIdentifierPatternString(self):
        """ correct pattern """
        self.assertEqual(self.node1obj1.getModelUniqueIdentifierPatternString(), "item__name")
        print("     pass: test_getModelUniqueIdentifierPatternString")
        
    # - - - - - - - - - - - - - - - - Plotting Models on Map - - - - - - - - - - - - - - - - - - - - -   
    def test_getMsgFromModel(self):
        """ Correct message for display """
        self.assertEqual(self.node1obj1.getMsgFromModel(), "(i1__n1)")
        print("     pass: test_getMsgFromModel")
        
    def test_getAllModelsFromUserAndUniqueSet(self):
        """ correct instance retrieval and fitlering of unique elements """
        allInstances, uniqueSet, identifiers = AbstractModelResultsTestClass.getAllModelsFromUserAndUniqueSet(self.user)
        # Unique elements
        self.assertEqual(('item','name'), identifiers)
        # All results (5 results)
        self.assertEqual(5, len(allInstances))
        # Unique Results (4 nodes)
        self.assertEqual(4, len(uniqueSet))
        print("     pass: test_getAllModelsFromUserAndUniqueSet")

    def test_unpackSpecificModelRequest(self):
        """ Checks the unique identifier fields can be retrieved from request """
        testReq = HttpRequest()
        testReq.GET._mutable = True
        testReq.GET['item']="i1"
        parsedReq, error = AbstractModelResultsTestClass.unpackSpecificModelRequest(testReq)
        # no error
        self.assertEqual(error, None)
        # only one field set in request
        self.assertEqual(1, len(parsedReq.keys()))
        # field was "i1"
        self.assertEqual("i1", parsedReq["item"])
        print("     pass: test_unpackSpecificModelRequest")
        
    def test_parseSpecificModelParamRequest(self):
        """ Checks correct results are retrieved from the dict generated above """
        # fetch all i1 (2 instances)
        results, displayMsg, reqParamString = AbstractModelResultsTestClass.parseSpecificModelParamRequest(self.user, {"item":"i1"})
        # check results
        self.assertEqual(2, len(results))
        self.assertEqual(displayMsg, "abstractmodelresultstestclass locations for: item=i1")
        self.assertEqual(reqParamString, "item=i1")
        # check results content
        self.assertEqual(results[0], self.node1obj1)
        self.assertEqual(results[1], self.node1obj2)
        print("     pass: test_parseSpecificModelParamRequest")
        
    # - - - - - - - - - - - - - - - - - - Network Graphs  - - - - - - - - - - - - - - - - - - - - - -
    def test_getNodeIdentifierFromDict(self):
        """ Checks node string conversion for dict<->nodeString for networks """
        egDict={"item":"i1", "name": "n1"}
        nodeString=AbstractModelResultsTestClass.getNodeIdentifierFromDict(egDict)
        # Check match
        self.assertEqual(nodeString, "i1__n1")
        print("     pass: test_getNodeIdentifierFromDict")
        
    def test_getNodeString(self):
        """ tests node string from object (which uses above method) """
        self.assertEqual(self.node1obj1.getNodeString(), "i1__n1")
        print("     pass: test_getNodeString")
        
    def test_getModelDictFromNodeString(self):
        """ from a model get the unqiuely identifying dict (used in node<->dict conversions above) from node string """
        self.assertDictEqual({"name":"n1","item":"i1"}, self.node1obj1.getModelDictFromNodeString("i1__n1"))
        print("     pass: getModelDictFromNodeString")
        

    
    def test_getNodesFromUser(self):
        """  all unique nodes from results of user """
        nodes = AbstractModelResultsTestClass.getNodesFromUser(self.user)
        # 5 results but only 4 unique nodes
        self.assertEqual(4, len(nodes))
        # check all expected nodes present
        for result in self.allResults:
            nodeString = result.getNodeString()
            for node in nodes:
                if node == nodeString:
                    break
            else:
                self.fail(f"{nodeString} not found in expected nodes: {nodes}")
        print("     pass: test_getNodesFromUser")
    
    def test_getNodeEdgesByLocationFromUser(self):
        """ correct co-location of nodes """
        edges, nodesWithEdges = AbstractModelResultsTestClass.getNodeEdgesByLocationFromUser(self.user)
        # 4 edges (see TestCase doc-string)
        self.assertEqual(len(edges), 4)
        # all nodes have >= 1 connection
        self.assertEqual(len(nodesWithEdges), 4)
        # edges are just sub-arrays of node-strings
        expectedEdges=[['i1__n1', 'i2__n2'], ['i1__n1', 'i3__n3'], ['i2__n2', 'i3__n3'],['i1__n1', 'i4__n4']]
        # check all expected edges present
        for edge in edges:
            for expectedEdge in expectedEdges:
                if edge == expectedEdge:
                    break
            else:
                self.fail(f"{edge} not found in expected edges: {expectedEdges}")
        print("     pass: test_getNodeEdgesByLocationFromUser")
     
    
    # @classmethod
    # def getNodeEdgesByLocationFromUser(self, user):

        
# class PersonTest(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.alice = Person.objects.create(first_name='Alice', last_name='Smith')
#         cls.bob = Person.objects.create(first_name='Bob', last_name='Smith')

#     def setUp(self):
#         self.alice.refresh_from_db()
#         self.bob.refresh_from_db()

#     def test_alice_first_name(self):
#         self.assertEqual(self.alice.first_name, 'Alice')

#     def test_bob_first_name(self):
#         self.assertEqual(self.bob.first_name, 'Bob')

#     def test_bob_first_name_modified(self):
#         self.bob.first_name = 'Jack'
#         self.bob.save()
#         self.assertEqual(self.bob.first_name, 'Jack')