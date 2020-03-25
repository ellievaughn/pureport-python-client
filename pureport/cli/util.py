from click import command, group, echo, pass_context, pass_obj
from functools import update_wrapper
from json import dumps
from inspect import isgeneratorfunction, isfunction, ismethod


def __create_client_group(f):
    """
    Constructs a Client Group command.

    Given a reference to the Client class function, e.g. the @property Client.accounts or
    instance function Client.AccountsClient.networks(account_id), this constructs a click.Group.

    It passes the parent context and parent obj (e.g. the parent Client class instance), then
    sets a new ctx.obj that is the invocation of this command.  We simply pass along any of
    *args and **kwargs down into the function.

    The `update_wrapper` is responsible for copying all the actual functions @option/@argument
    properties to the new function.

    Finally calling `group()(new_func)` creates the Group object and correctly parses all
    the parameters off the function.
    :param property|function f:
    :rtype: click.Group
    """
    actual_f = f.fget if isinstance(f, property) else f

    @pass_obj
    @pass_context
    def new_func(ctx, obj, *args, **kwargs):
        ctx.obj = actual_f(obj, *args, **kwargs)

    new_func = update_wrapper(new_func, actual_f)
    return group()(new_func)


def __create_client_command(f):
    """
    Constructs a Client Command.

    Given a reference to the Client class function, e.g. the Client.AccountClient.list,
    this constructs a click.Command.

    It passes the parent Group (see __create_client_group) obj (e.g. the Client class instance), then
    sets invokes the function reference using the parent context `obj` as the `self` argument
    of the command.

    The `update_wrapper` is responsible for copying all the actual functions @option/@argument
    properties to the new function.

    Finally calling `command()(new_func)` creates the Command object and correctly parses all
    the parameters off the function.
    :param property|function f:
    :rtype: click.Command
    """
    actual_f = f.fget if isinstance(f, property) else f

    @pass_obj
    def new_func(obj, *args, **kwargs):
        response = actual_f(obj, *args, **kwargs)
        # if the function returns a response, we'll just echo it as JSON
        if response is not None:
            echo(dumps(response))
        return response

    new_func = update_wrapper(new_func, actual_f)
    return command()(new_func)


def find_client_commands(obj):
    """
    Given an object, this finds a list of potential commands by
    listing all public attributes and returning the attributes
    that are functions.
    :param object obj:
    :rtype: list[function]
    """
    commands = []
    for name in dir(obj):
        if not name.startswith('_'):
            attr = getattr(obj, name)
            if isgeneratorfunction(attr) or isfunction(attr) or ismethod(attr):
                commands.append(attr)
    return commands


def construct_commands(commands):
    """
    Recursively construct a list of click.Command or click.Group and
    attach them to parent groups if necessary.
    :param list[function|ContextGroup] commands:
    :rtype: list[click.Command]
    """
    for cmd in commands:
        if isinstance(cmd, dict) and 'context' in cmd:
            grp = __create_client_group(cmd['context'])
            for child_cmd in construct_commands(cmd['commands']):
                grp.add_command(child_cmd)
            yield grp
        else:
            yield __create_client_command(cmd)
