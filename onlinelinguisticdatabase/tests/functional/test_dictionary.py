from onlinelinguisticdatabase.tests import *

class TestDictionaryController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='dictionary', action='index'))
        # Test response...
