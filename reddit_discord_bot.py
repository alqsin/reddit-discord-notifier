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

# TODO: initialization of a user should delete the previous notifications list probably
# TODO: rotate logs (rotatingfilehandler?)
# TODO: add more stuff to reddit_post, e.g. the description text
# TODO: better way of handling commands? discord.py has default method?
# TODO: welcome message (on startup + for new users)
# TODO: add console output for warnings/errors
# TODO: prevent the same alert from being added twice
# TODO: validate discord messages being sent (limits, valid characters, etc.)
# TODO: stop it from checking for notifications before the reddit bot is initialized (or set start_time to a little later)
# TODO: add (optional) pushover integration
# TODO: validate input for author (should be one word)
# TODO: (maybe) set reddit_fetcher to get a stream of posts, quit when they get too old (may minimize # of calls to reddit)
# TODO: don't need to access auth file repeatedly; only reading once on startup should work (maybe re-read when restarting bot)
# TODO: !restart
# TODO: timing changes based on subreddit

class MyClient(discord.Client):
	async def on_message(self,message):
		if not message.channel.is_private:
			pass
		elif message.content.lower() == 'hi' or message.content.lower() == 'hello':
			await client.send_message(message.channel,'Hello {}'.format(str(message.author.mention)))
		elif message.content.startswith('!'):
			try:
				result = await run_command(message)
				if result == 0:
					return
				else:
					await client.send_message(message.channel,result)
			except Exception as e:
				logging.exception("Issue running following command: {}.".format(message.content))
				await client.send_message(message.channel,"Error occurred, if you'd like, please PM {} complaining about this.".format(get_discord_admin()))
				# here we want to message the admin or something
				# also should probably add a validation making sure admin is in the discord server
	async def on_ready(self):
		logging.info("Hello")
		print('Logged in as')
		print(client.user.name)
		print(client.user.id)
		print('------')

def get_discord_token():
	return MY_AUTH['discord']['token']

def get_discord_admin():
	return MY_AUTH['discord']['admin']

def split_command(command):
	words = command.strip().split(' ')
	return words

def send_help():
	help_message = '''**Commands:**
	**!redditbot initialize**
	\tbecome a user of redditbot
	**!redditbot deinitialize**
	\tdelete your list
	**!redditbot list**
	\tprovides a list of alerts
	**!redditbot add [subreddit] [title|author] [search query]**
	\tadds an alert
	\tsearch query is of form [word1 word2 word3]
	\tmatch exact phrases by wrapping words like ["word1 word2" word3]
	\tprevent matching words by prefixing them with -, e.g. [word1 word2 -word3]
	**!redditbot remove [n]**
	\tremoves alert n (use !list to see alert numbers)
	'''
	return help_message

async def run_command(message):
	'''sends a command to run_general_command() or run_notification_command()'''
	admin_commands = ['!stop','!test']
	if any(message.content.startswith(command) for command in admin_commands):
		return await run_admin_command(message)
	elif str(message.channel) in notif.get_valid_users():
		return run_notification_command(message)
	else:
		return 0

def run_server_command(message):
	'''Runs a command. Must start with !redditbot
	Returns some string if it did something, 0 otherwise'''
	(command,command_body) = split_command(message.content)
	if not command[0] == '!redditbot' or not len(command) >= 2:
		return 0
	if command[1] == 'help':
		return send_help()
	elif command[1] == 'list':
		return notif.list_notifications(str(message.user.id))
	elif command[1] == 'add' and len(command) >= 3:
		return notif.add_notification("".join(command[2:]),str(message.user.id))
	elif command[1] == 'remove' and len(command) == 3:
		return notif.remove_notification(command[2],str(message.user.id))
	return "Not a valid command."

async def run_admin_command(message):
	'''Runs an administrative command in response to a PM.'''
	if not str(message.author) == get_discord_admin():
		return 0
	command = split_command(message.content)
	if command[0] == '!stop':
		set_exit_flag()
		logging.info("Shutting down.")
		await client.send_message(message.channel,'See you later!')
		await client.close()
	elif command[0] == '!test':
		return await test(message)
	return 0

async def message_user(user_id,message_text):
	'''Sends a message to user with id user_id.'''
	channel = client.get_channel(user_id)
	if channel is None:
		logging.error("Failed to find user with id {}".format(user_id))
		return 0
	await client.send_message(channel,message_text)
	return 1

async def test(message):
	return 'This is a test!'

async def check_notifications_periodically():
	notif.do_startup_routine()
	await client.wait_until_ready()
	start_time = datetime.utcnow()-timedelta(minutes=1)  # set initial start time
	while not RESTART_FLAG and not EXIT_FLAG:
		while client.is_closed and not (RESTART_FLAG or EXIT_FLAG):  # wait for client to be open if no flags are set
			logging.info("Client currently closed, waiting 15 seconds to check notifications.")
			await asyncio.sleep(15)
		end_time = datetime.utcnow()
		try:
			praw_instance = rdt.get_praw_instance(MY_AUTH['reddit'])
			all_notifications = notif.get_all_notifications()  # note that this is a dictionary
			for curr_sub in all_notifications:
				to_send = False
				try:
					to_send = rdt.check_one_subreddit(curr_sub,all_notifications[curr_sub],praw_instance,start_time,end_time)
				except Exception as e:
					logging.exception("Failure to check reddit posts for {}.".format(curr_sub))
				if to_send:
					for (curr_server,curr_channel,curr_user,curr_post) in to_send:
						await message_user(get_channel(curr_server,curr_channel),"**New reddit post matching your alert!**\n{}".format(str(curr_post)))
						await asyncio.sleep(0.002)  # sleep 2 ms to avoid the rate limit message
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

	MY_AUTH = settings_io.Auth()

	while not EXIT_FLAG:
		try:
			RESTART_FLAG = False
			MY_AUTH.read_auth()
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