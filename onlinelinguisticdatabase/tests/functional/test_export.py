from onlinelinguisticdatabase.tests import *

class TestExportController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='export', action='index'))
        # Test response...
