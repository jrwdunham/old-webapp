from onlinelinguisticdatabase.tests import *

class TestRpcserverController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='rpcserver', action='index'))
        # Test response...
