from collections.abc import Mapping


class DotDict(dict):

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            # TODO which is better?
            # return None
            raise AttributeError(name)

    def __setattr__(self, name, value):
        raise AttributeError('DotDict cannot set attributes')

    def __init__(self, some_dict=None):
        if isinstance(some_dict, dict):
            self.update(some_dict)
        elif some_dict is None:
            super(DotDict, self).__init__()
        else:
            raise TypeError('DotDict expects dict or None')

    def update(self, other_dict):
        for k, v in other_dict.items():
            if isinstance(v, Mapping):
                if k in self and isinstance(self[k], DotDict):
                    self[k].update(v)
                else:
                    self[k] = DotDict(v)
            else:
                self[k] = v

    @classmethod
    def from_module(cls, module):
        import inspect
        out = cls()
        for name, obj in inspect.getmembers(module):
            if (not name.startswith('__') and
                not inspect.ismodule(obj) and
                not inspect.isfunction(obj) and
                not inspect.isclass(obj)):
                out[name.lower()] = obj
        return out

