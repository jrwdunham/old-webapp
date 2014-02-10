from onlinelinguisticdatabase.tests import *

class TestAdministerController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='administer', action='index'))
        # Test response...
