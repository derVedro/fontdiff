import inspect
from collections.abc import Mapping

"""
Config is the main storage object that can be instantiated from another Config,
a dict or some module. It behaves a bit like a dict. Main advantage is that you
can access the members with dot. Config has an update() method just like the
dicts. If the Config contains a mapping, this mapping should be updated and not
replaced by other one.
"""


def _is_valid_member(name, obj) -> bool:
    return (
            not name.startswith('__') and
            not inspect.ismodule(obj) and
            not inspect.isfunction(obj) and
            not inspect.isclass(obj)
    )


def _is_mappable(obj) -> bool:
    return isinstance(obj, Config) or isinstance(obj, Mapping)


class Config:
    def __init__(self, source=None):
        if source is None:
            return
        elif _is_mappable(source):
            self.update(source)
        elif inspect.ismodule(source):
            self._update_from_module(source)
        else:
            raise TypeError(f"Unsupported source type: {type(source).__name__}")

    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"{cls.__name__} cannot be subclassed")

    def _update_from_module(self, module):
        for name, obj in inspect.getmembers(module):
            if _is_valid_member(name, obj):
                setattr(self, name.lower(), obj)
        return self

    def update(self, other):
        if inspect.ismodule(other):
            self._update_from_module(other)
            return
        # Normalize `other` to a dict-like view of (key, value) pairs
        if isinstance(other, Config) or isinstance(other, Mapping):
            items = other.items()
        else:
            raise TypeError(
                f"update() expected Config, mapping, or module; "
                f"got {type(other).__name__}"
            )
        for key, value in items:
            if not _is_valid_member(key, value):
                continue

            current = self.get(key)

            if _is_mappable(current) and _is_mappable(value):
                if not isinstance(current, self.__class__):
                    current = self.__class__(current)
                    setattr(self, key, current)
                current.update(value)
            else:
                setattr(self, key, value)

    def items(self):
        return self.__dict__.items()

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def __contains__(self, key):
        return key in self.__dict__