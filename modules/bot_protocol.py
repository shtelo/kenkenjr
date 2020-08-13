from discord import Message, Client


class Request:
    def __init__(self, message: Message = None, *, receiver: str = '', signal: str = '', addition: str = ''):
        if message is None:  # generate manually
            self.receiver = receiver
            self.signal = signal
            self.addition = addition
        else:  # generate from message
            self.message: Message = message
            tokens = message.content.split(' ', 2)
            length = len(tokens)
            self.receiver: str = tokens[0] if length >= 1 else None
            self.signal: str = tokens[1] if length >= 2 else None
            self.addition: str = tokens[2] if length >= 3 else None

    def __str__(self):
        return self.receiver + ' ' + self.signal + (' ' + self.addition if self.addition else '')

    def generate_respond(self, *, signal: str = '', addition: str = ''):
        return Request(receiver=self.message.author.mention, signal=signal, addition=addition)


class BotProtocol:
    ALL = 'ALL'

    ECHO = 'ECHO'
    PASS = 'PASS'
    SEND = 'SEND'
    HERE = 'HERE'
    DONE = 'DONE'

    SIGNALS = (ECHO, PASS, SEND, HERE, DONE)

    def __init__(self, client):
        self.client: Client = client

    def get_request(self, message: Message):
        request = Request(message)
        if message.author.id == self.client.user.id \
                or not message.author.bot \
                or request.receiver is None \
                or request.receiver not in (BotProtocol.ALL, f'<@{self.client.user.id}>', f'<@!{self.client.user.id}>')\
                or request.signal not in BotProtocol.SIGNALS:
            return
        return request

    async def on_message(self, message: Message):
        request = self.get_request(message)
        if request is None:
            return
        if request.signal == BotProtocol.ECHO:
            await self.on_echo(request)
        elif request.signal == BotProtocol.PASS:
            await self.on_pass(request)
        elif request.signal == BotProtocol.SEND:
            await self.on_send(request)
        elif request.signal == BotProtocol.HERE:
            await self.on_here(request)
        elif request.signal == BotProtocol.DONE:
            await self.on_done(request)

    async def on_echo(self, request: Request):
        pass

    async def on_pass(self, request: Request):
        pass

    async def on_send(self, request: Request):
        pass

    async def on_here(self, request: Request):
        pass

    async def on_done(self, request: Request):
        pass
