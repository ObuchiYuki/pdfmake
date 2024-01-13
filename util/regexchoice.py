import re

class RegexChoice(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def __contains__(self, val):
        return re.match(self.pattern, val)

    def __iter__(self):
        return iter([self.pattern])
