from onlinelinguisticdatabase.tests import *

class TestFormController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='form', action='index'))
        # Test response...
