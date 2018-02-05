import asyncio
from datetime import datetime,timedelta
import os

import logging
log_dir = 'logs/'
if not os.path.exists(log_dir):
		os.makedirs(log_dir)
logging.basicConfig(level=logging.INFO,format='%(asctime)s [%(levelname)s] - %(message)s',filename=os.path.join(log_dir,'default_log.log'))

import discord
import settings_io
import notifications_handler as notif
import reddit_fetcher as rdt

client = discord.Client()

# TODO: add initialization method that sets admin, creates necessary folder structure, etc.
# TODO: create 'community' mode that has subreddit-based channels and pings users (and keeps user-based lists still)
# TODO: initialization of a user should delete the previous notifications list probably
# TODO: rotate logs (rotatingfilehandler?)
# TODO: add more stuff to reddit_post, e.g. the description text
# TODO: better way of handling commands? discord.py has default method?
# TODO: welcome message (on startup + for new users)
# TODO: remove user function <-- what did I mean by this?
# TODO: have settings by server?
# TODO: change ! commands to reflect the bot name
# TODO: add comments
# TODO: add console output for warnings
# TODO: prevent the same alert from being added twice
# TODO: validate discord messages being sent (limits, valid characters, etc.)
# TODO: stop it from checking for notifications before the reddit bot is initialized (or set start_time to a little later)
# TODO: implement checking by post-id, as if the post is 'invisible' during the first few minutes after it is posted it will be ignored
# TODO: add (optional) pushover integration

# def initialize_logger(logger_name):
# 	log_file = os.path.join(log_dir,logger_name+'.log')
# 	log = logging.getLogger(logger_name)
# 	log_fh = logging.FileHandler(log_file)
# 	log_fh.setLevel(logging.INFO)
# 	log_fmt = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
# 	log_fh.setFormatter(log_fmt)
# 	log.addHandler(log_fh)
# 	log.propagate = False
# 	return log

def get_discord_auth():
	AUTH_FILE = 'auth.ini'
	AUTH_ENTRY = 'discord'
	AUTH_VALUES = ['token','admin']
	return settings_io.read_auth(AUTH_FILE,AUTH_ENTRY,AUTH_VALUES)

def get_discord_token():
	return get_discord_auth()['token']

# TODO: add validation here?
def get_discord_admin():
	return get_discord_auth()['admin']

def split_command(command):
	words = command.split(' ',1)
	if len(words) == 1:
		return (words[0],None)
	return (words[0],words[1])

def send_help():
	help_message = '''**Commands:**
	**!list**
	\tprovides a list of alerts
	**!add [subreddit] [title|author] [search query]**
	\tadds an alert
	\tsearch query is of form [word1 word2 word3]
	\tmatch exact phrases by wrapping words like ["word1 word2" word3]
	\tprevent matching words by prefixing them with -, e.g. [word1 word2 -word3]
	**!remove [n]**
	\tremoves alert n (use !list to see alert numbers)
	**!undo**
	\treverts last change made to list of alerts
	'''
	return help_message

async def run_command(message):
	'''sends a command to run_general_command() or run_notification_command()'''
	if str(message.channel) == 'general':
		return await run_general_command(message)
	elif str(message.channel) in notif.get_valid_users():
		return await run_notification_command(message)
	else:
		return 0

# TODO: use the native command handling instead of this
async def run_notification_command(message):
	'''runs a command in a notification channel
	returns some string if it did something, 0 otherwise'''
	(command,command_body) = split_command(message.content)
	if command == '!add':
		return notif.add_notification(command_body,message.channel.name)
	elif command == '!remove':
		return notif.remove_notification(command_body,message.channel.name)
	elif command == '!list':
		return notif.list_notifications(message.channel.name)
	elif command == '!undo':
		return notif.undo_last_change(message.channel.name)
	elif command == '!help':
		return send_help()
	# elif command == '!clear':
	# 	return clear_messages(message.channel)
	return 0

# async def clear_messages(channel):
# 	tmp = await client.send_message(channel, 'Clearing messages...')
# 	async for msg in client.logs_from(channel):
# 		await client.delete_message(msg)
# 	return "Cleared channel of messages."

async def run_general_command(message):
	'''runs a command in #general
	returns some string if it did something, 0 otherwise'''
	(command,command_body) = split_command(message.content)
	if command == '!stop':
		if str(message.author) == get_discord_admin():
			await client.send_message(message.channel,'See you later!')
			logging.info("Shutting down.")
			await client.close()
			exit()
		else:
			#await client.send_message(message.channel,'No.')
			return 0
	elif command == '!initialize':
		if str(message.author) == get_discord_admin():
			return await initialize_user(command_body,message.server)
	elif command == '!test':
		if str(message.author) == get_discord_admin():
			return await test(message)
	# elif command == '!clear':
	# 	if str(message.author) == get_discord_admin():
	# 		return await clear_messages(message.channel)
	return 0

async def message_user(channel_id,message_text):
	'''sends a message to a user via channel, which should be their user id'''
	message_to_send = ""
	user = await client.get_user_info(channel_id)
	if user is not None:
		message_to_send += user.mention + '\n'
	message_to_send += message_text
	channel = client.get_channel(channel_id)
	if channel is None:
		logging.error("Failed to get channel with id {}".format(channel_id))
		return 0
	await client.send_message(client.get_channel(channel_id),message_to_send)
	return 0

async def initialize_user(user_name,server):
	'''Creates a new channel with name 'user,' adds user to channel, and adds channel_id as an entry to users.ini'''
	user = discord.utils.get(server.members,name=user_name)
	if user is None:
		return "Couldn't find user."
	possible_channel = discord.utils.get(server.channels,name=str(user.id))
	if possible_channel is not None:
		await client.delete_channel(possible_channel)
	no_read = discord.PermissionOverwrite(read_messages=False)  # probably make this a little more robust
	yes_read = discord.PermissionOverwrite(read_messages=True)
	new_channel = await client.create_channel(server, user.id, (server.default_role, no_read), (server.me, yes_read), (user, yes_read))
	notif.add_user(str(user.id),new_channel.id)
	return "Initialized user {} (id={})".format(user.mention,str(user.id))

async def test(message):
	return 0

@client.event
async def on_ready():
	logging.info("Hello")
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')
 
# stopping this works rather poorly, should probably find a cleaner method
async def check_notifications_periodically():
	await client.wait_until_ready()
	start_time = datetime.utcnow() - timedelta(minutes=5)
	while not client.is_closed:
		end_time = datetime.utcnow()
		try:
			praw_instance = rdt.get_praw_instance()
			all_notifications = notif.get_all_notifications()  # note that this is a dictionary
			to_send = False
			for curr_sub in all_notifications:
				try:
					to_send = rdt.check_one_subreddit(curr_sub,all_notifications[curr_sub],praw_instance,start_time,end_time)
				except Exception as e:
					logging.exception("Failure to check reddit posts for {}.".format(curr_sub))
			if to_send:
				for curr_to_send in to_send:
					await message_user(notif.get_user_channel_id(curr_to_send[0]),"**New reddit post matching your alert!**\n{}".format(str(curr_to_send[1])))
			logging.info("Checked notifications from {} to {}".format(start_time.strftime('%Y-%m-%d %H:%M:%S'),end_time.strftime('%Y-%m-%d %H:%M:%S')))
		except Exception as e:
			logging.exception("Issue checking notifications.")
		start_time = end_time
		await asyncio.sleep(60)  # later will change this to be based on timestamp instead of just sleeping for 60s I guess

@client.event
async def on_message(message):
	if message.content == 'hi' or message.content == 'Hi' or message.content == 'Hello' or message.content == 'hello':
		await client.send_message(message.channel,'Hello {}'.format(str(message.author.mention)))
	elif message.content.startswith('!'):
		try:
			result = await run_command(message)
			if result == 0:
				return
			else:
				await client.send_message(message.channel,result)
		except Exception as e:
			logging.exception("Issue running ! command.")
			await client.send_message(message.channel,"Error occurred, please PM someone complaining about this.")
			# here we want to message the admin or something
			# also should probably add a validation making sure admin is in the discord server

#main_log = initialize_logger('discord_bot')
#reddit_log = initialize_logger('reddit')

client.loop.create_task(check_notifications_periodically())
client.run(get_discord_token())