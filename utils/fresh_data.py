from datetime import datetime


class FreshData:
    def __init__(self, data, expire_after):
        self._data = data
        self.timestamp = datetime.now()
        self.expire_after = expire_after  # seconds

    @property
    def data(self):
        if (datetime.now() - self.timestamp).total_seconds() > self.expire_after:
            self._data = None
        return self._data
