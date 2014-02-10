from onlinelinguisticdatabase.tests import *

class TestMorphparserController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='morphparser', action='index'))
        # Test response...
