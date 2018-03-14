import re
from . import Storer

class StencilaStorer(Storer):
    name = 'stencila'

    def valid_path(self, path):
        self.path = path
        m = re.match('^(?P<owner>[a-z0-9-]+)/(?P<project_name>[a-z0-9-]+)$', self.path)
        if not m:
            return False
        self.owner = m.group('owner')
        self.project_name = m.group('project_name')
        return True