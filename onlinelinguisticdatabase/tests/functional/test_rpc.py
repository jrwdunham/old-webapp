from onlinelinguisticdatabase.tests import *

class TestRpcController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='rpc', action='index'))
        # Test response...
