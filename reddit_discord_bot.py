import asyncio
from datetime import datetime,timedelta
import os
import time  # for sleeping in body

import discord
import settings_io
import notifications_handler as notif
import reddit_fetcher as rdt

import logging
from logging.handlers import TimedRotatingFileHandler

log_dir = 'logs/'
if not os.path.exists(log_dir):
		os.makedirs(log_dir)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

# set main logger
handler = TimedRotatingFileHandler(os.path.join(log_dir,'main.log'),when="midnight",interval=1)
handler.setFormatter(formatter)
handler.suffix = "%Y%m%d"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# set discord.py logger
dp_handler = TimedRotatingFileHandler(os.path.join(log_dir,'discordpy.log'),when="midnight",interval=1)
dp_handler.setFormatter(formatter)
dp_handler.suffix = "%Y%m%d"

dp_logger = logging.getLogger('discord')
dp_logger.setLevel(logging.INFO)
dp_logger.addHandler(dp_handler)

# TODO: rotate logs (rotatingfilehandler?)
# TODO: add more stuff to reddit_post, e.g. the description text
# TODO: better way of handling commands?
# TODO: welcome message for people joining server (would have to be a separate 'bot' I suppose)
# TODO: add console output for warnings/errors
# TODO: prevent the same alert from being added twice
# TODO: validate input for author (should be one word)
# TODO: catalog already-checked post ids and check more than just past minute (ignoring previously checked posts)
# TODO: don't need to access auth file repeatedly; only reading once on startup should work (maybe re-read when restarting bot)
# TODO: !restart
# TODO: timing changes based on subreddit

class MyClient(discord.Client):
	async def on_message(self,message):
		if not message.channel.is_private:
			pass
		elif message.content.lower() == 'hi' or message.content.lower() == 'hello':
			await client.send_message(message.channel,'Hello {}'.format(str(message.author)))
		elif message.content.startswith('!'):
			try:
				result = await run_command(message)
				if result == 0:
					return
				else:
					await message_channel(message.channel,result)
			except Exception as e:
				logger.exception("Issue running following command: {}.".format(message.content))
				await client.send_message(message.channel,"Error occurred, if you'd like, please complain in #help.")
				# here we want to message the admin or something
				# also should probably add a validation making sure admin is in the discord server
	async def on_ready(self):
		logger.info("Hello")
		print('Logged in as')
		print(client.user.name)
		print(client.user.id)
		print('------')

def get_discord_token():
	return MY_AUTH['discord']['token']

def get_discord_admin():
	return MY_AUTH['discord']['admin']

def send_help():
	help_message = '''**Commands:**
	**!initialize**
	\tinitialize list; must be done to add/receive notifications
	**!deinitialize**
	\tdelete your list
	**!list**
	\tprovides a list of alerts
	**!add [subreddit] [title|author] [search query]**
	\tadds an alert
	\tsearch query is of form [word1 word2 word3] (without brackets)
	\tmatch exact phrases by wrapping words like ["word1 word2" word3]
	\tprevent matching words by prefixing them with -, e.g. [word1 word2 -word3]
	\texample usage: !add buildapcsales title nvidia gpu
	**!remove [n]**
	\tremoves alert n (use !list to see alert numbers)
	'''
	return help_message

async def run_command(message):
	'''Runs a command, with various checks to see if commands are valid.'''
	command = message.content.lower().strip().split(' ')
	if command[0] == '!help':
		return send_help()
	elif command[0] == '!initialize':
		return notif.initialize_user(str(message.author.id))
	elif not notif.validate_user(str(message.author.id)):
		return 'Type !help for help!'
	elif command[0] == '!list':
		return notif.list_notifications(str(message.author.id))
	elif command[0] == '!add':
		return notif.add_notification(" ".join(command[1:]),str(message.author.id))
	elif command[0] == '!remove':
		return notif.remove_notification(command[1],str(message.author.id))
	elif command[0] == '!deinitialize':
		return notif.deinitialize_user(str(message.author.id))
	elif command[0] == '!stop' and str(message.author) == get_discord_admin():
		await client.send_message(message.channel,'See you later!')
		return await client_exit()
	elif command[0] == '!test' and str(message.author) == get_discord_admin():
		return await test(message)
	return 0

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

async def message_channel(channel,message_text):
	'''Sends a message to a channel.
	If message is too long, splits message based on CHUNK_SIZE.'''
	CHUNK_SIZE = 1999  # max message length allowed

	if len(message_text) <= CHUNK_SIZE:
		await client.send_message(channel,message_text)
	else:
		messages = split_message(message_text,CHUNK_SIZE)
		if messages is None:
			await client.send_message(channel,'Message was too long to send. If there\'s no reason for this, go complain in #help.')
		for message in messages:
			await client.send_message(channel,message)
	return 0

async def message_user(user_id,message_text):
	'''Sends a private message to user with id user_id.
	If message is too long, splits message first.'''
	CHUNK_SIZE = 1999  # max message length allowed

	channel = client.get_channel(user_id)
	if channel is None:
		logger.error("Failed to find user with id {}".format(user_id))
		return 0

	return message_channel(channel,message_text)
	
async def test(message):
	return 'This is a test!'

async def client_exit():
	'''Sets event loop exit flag and shuts down discord connection.'''
	set_exit_flag()
	logger.info("Shutting down.")
	await asyncio.sleep(90)
	await client.close()
	return 0

async def check_notifications_periodically():
	'''Every 60 seconds + run time, checks notifications. Meant to run in an event loop.'''
	notif.do_startup_routine()
	await client.wait_until_ready()
	start_time = datetime.utcnow()-timedelta(minutes=1)  # set initial start time
	while not (RESTART_FLAG or EXIT_FLAG):
		while client.is_closed and not (RESTART_FLAG or EXIT_FLAG):  # wait for client to be open if no flags are set
			logger.info("Client currently closed, waiting 15 seconds to check notifications.")
			await asyncio.sleep(15)
		end_time = datetime.utcnow()
		try:
			praw_instance = rdt.get_praw_instance(MY_AUTH['reddit api'])
			# TODO: this is stupid, get notification by user (or have it in a data structure where users are roots)
			all_notifications = notif.get_all_notifications()  # note that this is a dictionary
			for curr_sub in all_notifications:
				to_send = False
				try:
					to_send = rdt.check_one_subreddit(curr_sub,all_notifications[curr_sub],praw_instance,start_time,end_time)
				except Exception as e:
					logger.exception("Failure to check reddit posts for {}.".format(curr_sub))
				if to_send:
					for (curr_user,curr_post) in to_send:
						await message_user(curr_user,"**New reddit post matching your alert!**\n{}".format(str(curr_post)))
			logger.info("Checked posts from {} to {}".format(start_time.strftime('%Y-%m-%d %H:%M:%S'),end_time.strftime('%Y-%m-%d %H:%M:%S')))
		except Exception as e:
			logger.exception("Issue checking notifications.")
		start_time = end_time
		await asyncio.sleep(60)  # I guess it doesn't matter if it checks exactly every minute
	logger.info("Exit or restart flag found, closing notification checking loop.")
	return

def set_exit_flag():
	global EXIT_FLAG
	EXIT_FLAG = True

if __name__ == "__main__":

	EXIT_FLAG = False  # changed via set_exit_flag()
	RESTART_FLAG = False

	MY_AUTH = settings_io.Auth()

	while not EXIT_FLAG or RESTART_FLAG:
		try:
			RESTART_FLAG = False
			MY_AUTH.read_auth()
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
			client = MyClient()
			loop.create_task(check_notifications_periodically())
			loop.run_until_complete(client.start(get_discord_token()))
		except Exception as e:
			logger.exception("Discord bot exited with an exception.")
		if not (RESTART_FLAG or EXIT_FLAG):
			RESTART_FLAG = True  # if it reaches this point, the client exited for some unknown reason, so restart
		if not client.is_closed:
			logger.info("Closing and restarting client.")
			client.close()
		if not loop.is_closed():
			logger.info("Closing and restarting loop.")
			loop.close()

	logger.info("Reached end of program.")