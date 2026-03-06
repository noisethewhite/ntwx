import collections.abc as cabc
import typing as t
import threading
import inspect


_T = t.TypeVar("_T")
_R = t.TypeVar("_R")
_P = t.ParamSpec("_P")


class Singleton(type):
    _instances: dict[type, object] = {}
    _locks: dict[type, threading.Lock] = {}

    def __new__(mcls, name: str, bases: tuple[type, ...],
                namespace: dict[str, t.Any], **kwargs: t.Any) -> type:
        """
        Prevent singletons from taking args in __init__.
        """
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        init = namespace.get("__init__")
        if init is not None:
            sig = inspect.signature(init)
            if len(sig.parameters) != 1:
                raise TypeError(f"{name}.__init__ must only accept 1 argument: self.")
        return cls

    def __reduce__(self) -> tuple[type, tuple[()]]:
        """
        Prevent class duplication as a result of unpickling.
        """
        return (type(self), ())

    def __call__(cls, *args: t.Any, **kwargs: t.Any) -> t.Any:
        mcls = type(cls)
        inst = mcls._instances.get(cls)
        if inst is None:
            if mcls._locks.get(cls) is None:
                mcls._locks[cls] = threading.Lock()
            with mcls._locks[cls]:
                inst = mcls._instances.get(cls)
                if inst is None:
                    inst = super().__call__(*args, **kwargs)
                    mcls._instances[cls] = inst
        return inst


class singletonproperty(t.Generic[_T, _R]):
    _func: cabc.Callable[[_T], _R]

    def __init__(self, func: cabc.Callable[[_T], _R]) -> None:
        self._func = func

    def __get__(self, _: t.Optional[_T], owner: type[_T]) -> _R:
        if not isinstance(owner, Singleton):
            raise TypeError("singletonproperty must only be used inside a Singleton.")
        instance = owner()
        return self._func(instance)


class singletonmethod(t.Generic[_T, _P, _R]):
    _func: cabc.Callable[t.Concatenate[_T, _P], _R]

    def __init__(self, func: cabc.Callable[t.Concatenate[_T, _P], _R]) -> None:
        self._func = func

    def __get__(self, _: t.Optional[_T], owner: type[_T]) -> cabc.Callable[_P, _R]:
        if not isinstance(owner, Singleton):
            raise TypeError("singletonmethod must only be used inside a Singleton.")
        def method(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            instance = owner()
            return self._func(instance, *args, **kwargs)
        return method
