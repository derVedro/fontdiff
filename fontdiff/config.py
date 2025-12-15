class Config:

    def __init__(self, some_config=None):
        if isinstance(some_config, self.__class__):
            self.update_from_dict(some_config.__dict__)

    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"{cls.__name__} cannot be subclassed")

    def update_from_dict(self, some_dict):
        self.__dict__.update(some_dict)
        return self

    def update_from_module(self, module):
        import inspect
        dic = self.__dict__
        for name, obj in inspect.getmembers(module):
            if (not name.startswith('__') and
                not inspect.ismodule(obj) and
                not inspect.isfunction(obj) and
                not inspect.isclass(obj)):
                dic[name.lower()] = obj
        return self

    def update(self, other_config):
        self.update_from_dict(other_config.__dict__)
        return self

    def get(self, key, default=None):
        return self.__dict__.get(key, default)
