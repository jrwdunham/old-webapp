from onlinelinguisticdatabase.tests import *

class TestHomeController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='home', action='index'))
        # Test response...
