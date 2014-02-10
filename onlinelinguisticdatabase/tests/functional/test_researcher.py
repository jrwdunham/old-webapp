from onlinelinguisticdatabase.tests import *

class TestResearcherController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='researcher', action='index'))
        # Test response...
