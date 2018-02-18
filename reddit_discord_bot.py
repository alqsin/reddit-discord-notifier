import asyncio
from datetime import datetime,timedelta
import os
import time  # for sleeping in body

import logging
log_dir = 'logs/'
if not os.path.exists(log_dir):
		os.makedirs(log_dir)
logging.basicConfig(level=logging.INFO,format='%(asctime)s [%(levelname)s] - %(message)s',filename=os.path.join(log_dir,'default_log.log'))

import discord
import settings_io
import notifications_handler as notif
import reddit_fetcher as rdt

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
# TODO: delay between sending messages to discord
# TODO: validate input for author (should be one word)
# TODO: (maybe) set reddit_fetcher to get a stream of posts, quit when they get too old (may minimize # of calls to reddit)
# TODO: validate search term input (shlex doesn't like mixed single and double quotes)
# TODO: don't need to access auth file repeatedly; only reading once on startup should work (maybe re-read when restarting bot)
# TODO: !restart

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

class MyClient(discord.Client):
	async def on_message(self,message):
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
	async def on_ready(self):
		logging.info("Hello")
		print('Logged in as')
		print(client.user.name)
		print(client.user.id)
		print('------')

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
	return 0

async def run_general_command(message):
	'''runs a command in #general
	returns some string if it did something, 0 otherwise'''
	(command,command_body) = split_command(message.content)
	if command == '!stop':
		if str(message.author) == get_discord_admin():
			set_exit_flag()
			logging.info("Shutting down.")
			await client.send_message(message.channel,'See you later!')
			await client.close()
	elif command == '!initialize':
		if str(message.author) == get_discord_admin():
			return await initialize_user(command_body,message.server)
	elif command == '!test':
		if str(message.author) == get_discord_admin():
			return await test(message)
	return 0

async def message_user(channel_id,message_text):
	'''sends a message to a user via channel, which should be their user id'''
	channel = client.get_channel(channel_id)
	if channel is None:
		logging.error("Failed to get channel with id {}".format(channel_id))
		return 0
	message_to_send = ""
	try:
		user = await client.get_user_info(channel.name)  # going to have to change this when updating structure
		message_to_send += user.mention + '\n'
	except NotFound as e:
		logging.error("No user matching channel name {}.".format(channel.name))
	message_to_send += message_text
	await client.send_message(channel,message_to_send)
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

async def check_notifications_periodically():
	await client.wait_until_ready()
	start_time = datetime.utcnow()-timedelta(minutes=1)  # set initial start time
	while not RESTART_FLAG and not EXIT_FLAG:
		while client.is_closed and not (RESTART_FLAG or EXIT_FLAG):  # wait for client to be open if no flags are set
			logging.info("Client currently closed, waiting 15 seconds to check notifications.")
			await asyncio.sleep(15)
		end_time = datetime.utcnow()
		try:
			praw_instance = rdt.get_praw_instance()
			all_notifications = notif.get_all_notifications()  # note that this is a dictionary
			for curr_sub in all_notifications:
				to_send = False
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
		await asyncio.sleep(60)  # I guess it doesn't matter if it checks exactly every minute
	logging.info("Exit or restart flag found, closing notification checking loop.")
	return

def set_exit_flag():
	global EXIT_FLAG
	EXIT_FLAG = True

if __name__ == "__main__":

	EXIT_FLAG = False

	while not EXIT_FLAG:
		try:
			RESTART_FLAG = False
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
			client = MyClient()
			loop.create_task(check_notifications_periodically())
			loop.run_until_complete(client.start(get_discord_token()))
		except Exception as e:
			logging.exception("Discord bot exited with an exception.")
		if not (RESTART_FLAG or EXIT_FLAG):
			RESTART_FLAG = True  # if it reaches this point, the client exited for some unknown reason, so restart
		if not client.is_closed:
			logging.info("Closing and restarting client.")
			client.close()
		if not loop.is_closed():
			logging.info("Closing and restarting loop.")
			loop.close()
		time.sleep(120)

	logging.info("Reached end of program.")