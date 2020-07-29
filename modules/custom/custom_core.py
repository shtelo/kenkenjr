from discord.ext.commands import Command, Group, GroupMixin

from kenkenjr.utils import get_brief, get_help


class CustomGroupMixin(GroupMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            kwargs.setdefault('parent', self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.group` and adds it to
        the internal command list via :meth:`~.GroupMixin.add_command`.
        """

        def decorator(func):
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class CustomCommand(CustomGroupMixin, Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        name = kwargs.get('name')
        if self.full_parent_name:
            name = self.full_parent_name + ' ' + name
        self.brief = get_brief(name)
        self.help = get_help(name)


class CustomGroup(CustomCommand, Group):
    def __init__(self, func, **attrs):
        super().__init__(func, **attrs)


def command(name=None, cls=None, **attrs):
    if cls is None:
        cls = CustomCommand

    def decorator(func):
        if isinstance(func, Command):
            raise TypeError('Callback is already a command.')
        return cls(func, name=name, **attrs)

    return decorator


def group(name=None, **attrs):
    """A decorator that transforms a function into a :class:`.Group`.

    This is similar to the :func:`.command` decorator but the ``cls``
    parameter is set to :class:`Group` by default.

    .. versionchanged:: 1.1
        The ``cls`` parameter can now be passed.
    """

    attrs.setdefault('cls', CustomGroup)
    return command(name=name, invoke_without_command=True, **attrs)
