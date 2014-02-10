from onlinelinguisticdatabase.tests import *

class TestDebugController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='debug', action='index'))
        # Test response...
