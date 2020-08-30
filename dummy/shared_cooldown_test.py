from contextvars import Context

from discord.ext.commands import Bot, Cooldown, CooldownMapping, Command, BucketType, Group

bot = Bot(';')


def shared_cooldown(rate, per, type=BucketType.default):
    cooldown = Cooldown(rate, per, type)
    cooldown_mapping = CooldownMapping(cooldown)

    def decorator(func):
        if isinstance(func, Command):
            func._buckets = cooldown_mapping
        else:
            func.__commands_cooldown__ = cooldown
        print(func, end=' ')
        print(cooldown_mapping)
        return func
    return decorator


cooldown_test = shared_cooldown(1, 10, BucketType.channel)


def print_commands(commands: set):
    for command in commands:
        print(command, end=' ')
        print(type(command), end=' ')
        print(command._buckets)
        if isinstance(command, Group):
            print_commands(command.commands)


@bot.group(name='t', invoke_without_command=True)
@cooldown_test
async def t(ctx: Context):
    await ctx.send('t')
    print_commands(bot.commands)


@t.command(name='1')
@cooldown_test
async def t1(ctx: Context):
    await ctx.send('t1')


@bot.command(name='t2')
@cooldown_test
async def t2(ctx: Context):
    await ctx.send('t2')

bot.run('NTg3MTYyNDg3ODQyMDEzMTg0.XPyjrg.VrJlH6jVghb_WHDggia58QIvQwI')
