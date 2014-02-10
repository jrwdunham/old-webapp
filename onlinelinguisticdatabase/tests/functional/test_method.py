from onlinelinguisticdatabase.tests import *

class TestMethodController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='method', action='index'))
        # Test response...
