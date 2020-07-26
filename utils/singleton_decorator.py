def singleton(_cls):
    class Singletonized(_cls):
        _instance = None

        def __new__(cls, *args, **kwargs):
            if Singletonized._instance is None:
                Singletonized._instance = _cls(*args, **kwargs)
            return Singletonized._instance

    return Singletonized
