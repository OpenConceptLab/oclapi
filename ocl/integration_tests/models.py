class TestStream(object):
    def __init__(self):
        self.value = ''
    def write(self, line, ending=''):
        self.value = self.value + line
    def getvalue(self):
        return self.value
    def flush(self):
        return self.value
    def close(self):
        return self.value
