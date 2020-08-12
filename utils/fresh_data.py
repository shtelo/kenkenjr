from datetime import datetime


class FreshData:
    def __init__(self, data):
        self.data = data
        self.timestamp = datetime.now()
