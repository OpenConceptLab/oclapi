__author__ = 'misternando'


class MockRequest(object):
    method = 'POST'
    user = None

    def __init__(self, user):
        self.user = user