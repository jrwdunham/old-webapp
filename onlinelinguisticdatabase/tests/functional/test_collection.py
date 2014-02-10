from onlinelinguisticdatabase.tests import *

class TestCollectionController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='collection', action='index'))
        # Test response...
