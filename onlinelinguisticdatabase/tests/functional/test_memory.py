from onlinelinguisticdatabase.tests import *

class TestMemoryController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='memory', action='index'))
        # Test response...
