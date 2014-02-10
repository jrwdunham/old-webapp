from onlinelinguisticdatabase.tests import *

class TestRpcclientController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='rpcclient', action='index'))
        # Test response...
