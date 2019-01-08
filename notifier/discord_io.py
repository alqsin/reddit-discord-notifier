import asyncio
import discord
import settings_io
import data_io

class PMClient(discord.Client):
    def __init__(self, logger):
        super().__init__()
        self.EXIT_FLAG = False
        self.RESTART_FLAG = False
        self.AUTH = settings_io.read_auth()
        self.logger = logger

    async def start(self):
        return await super().start(self.AUTH['discord']['token'])

    async def on_message(self, message):
        if not message.channel.is_private:
            pass
        elif (message.content.lower() == 'hi' or
              message.content.lower() == 'hello'):
            await self.send_message(
                message.channel,'Hello {}'.format(str(message.author)))
        elif message.content.startswith('!'):
            try:
                result = await self.run_command(message)
                if result == 0:
                    return
                else:
                    await self.message_channel(message.channel, result)
            except Exception:
                self.logger.exception(
                    "Issue running following command: {}.".format(message.content))
                await self.send_message(
                    message.channel,
                    "Some error occurred while processing your command.")

    async def on_ready(self):
        self.logger.info("Hello")
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def message_channel(self, channel, message_text):
        '''Sends a message to a channel (channel can also be a user).
        If message is too long, splits message based on CHUNK_SIZE.'''
        CHUNK_SIZE = 1999  # max message length allowed

        if len(message_text) <= CHUNK_SIZE:
            await self.send_message(channel,message_text)
        else:
            messages = split_message(message_text,CHUNK_SIZE)
            if messages is None:
                await self.send_message(channel,
                    "Message was too long to send."
                    "If there's no reason for this, go complain in #help.")
            for message in messages:
                await self.send_message(channel,message)
        return 0

    async def message_user(self, user_id, message_text):
        '''Sends a private message to user with id user_id.
        If message is too long, splits message first.'''
        user = discord.utils.get(self.get_all_members(), id=user_id)

        return await self.message_channel(user,message_text)

    async def run_command(self, message):
        '''Runs a command, with various checks to see if commands are valid.'''
        command = message.content.lower().strip().split(' ')
        if command[0] == '!help':
            return send_help()
        elif command[0] == '!stop' and str(message.author) == self.AUTH['discord']['admin']:
            await self.send_message(message.channel,'See you later!')
            return await self.exit()
        elif command[0] == '!test' and str(message.author) == self.AUTH['discord']['admin']:
            return await self.test(message)
        elif command[0] == '!initialize':
            return data_io.initialize_user(str(message.author.id))
        elif not data_io.validate_user(str(message.author.id)):
            return 'Type !help for help!'
        elif command[0] == '!list':
            return data_io.list_notifications(str(message.author.id))
        elif command[0] == '!add':
            return data_io.add_notification(" ".join(command[1:]),str(message.author.id))
        elif command[0] == '!remove':
            return data_io.remove_notification(command[1],str(message.author.id))
        elif command[0] == '!deinitialize':
            return data_io.deinitialize_user(str(message.author.id))
        return 0

    async def test(self, message):
        return 'This is a test!'

    async def exit(self):
        '''Sets event loop exit flag and shuts down discord connection.'''
        self.EXIT_FLAG = True
        self.logger.info("Shutting down.")
        await asyncio.sleep(90)
        await self.close()
        return 0

def send_help():
    help_message = '''```Commands:
    !initialize
    \tinitialize list; must be done to add/receive notifications
    !deinitialize
    \tdelete your list
    !list
    \tprovides a list of alerts
    !add [subreddit] [title|author] [search query]
    \tadds an alert
    \tsearch query is of form [word1 word2 word3] (without brackets)
    \tmatch phrases by wrapping words with quotes, e.g. ["word1 word2" word3]
    \tprevent matching words by prefixing them with -, e.g. [word1 word2 -word3]
    \texample usage: !add buildapcsales title nvidia gpu
    !remove [n]
    \tremoves alert n (use !list to see alert numbers)```'''

    help_message = help_message.replace('\n    ','\n')
    return help_message

def split_message(message,CHUNK_SIZE):
    '''Splits message into chunks smaller than (or equal in length to)
    CHUNK_SIZE.'''
    messages = []
    shortened_message = ''
    for line in message.split('\n'):
        if len(line) > CHUNK_SIZE:
            return None
        if len(line) + len(shortened_message) > CHUNK_SIZE:
            messages.append(shortened_message.strip())
            shortened_message = line
        else:
            shortened_message += '\n' + line
    messages.append(shortened_message.strip())
    return messages
