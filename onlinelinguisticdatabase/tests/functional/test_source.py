from onlinelinguisticdatabase.tests import *

class TestSourceController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='source', action='index'))
        # Test response...
