import settings_io
import os
import reddit_fetcher as rdt

from misc_methods import *

def notification_to_str(notification):
	return "Subreddit: /r/{}\nType: {}\nQuery: {}\n".format(notification['sub'],notification['type'],notification['query'])

def get_user_path(user):
	return os.path.join('users',str(user))

# probably want to validate subreddit before adding
def add_notification(text,user):
	'''Format for notification text should be [subreddit] [type] [search query]'''
	user_path = get_user_path(user)
	if user_path is None:
		return "User not found."

	split_text = text.split(' ',2)
	if len(split_text) != 3:
		return "Invalid alert format, please try again."
	
	sub = split_text[0]
	query_type = split_text[1]
	query = split_text[2]

	if not rdt.validate_subreddit(sub):
		return ("Invalid subreddit.")
	if not (query_type == 'title' or query_type == 'author'):
		return "Query type must be title or author."

	new_notification = {'sub':split_text[0],'type':split_text[1],'query':split_text[2]}
	settings_io.add_config_item(user_path,new_notification)

	return "**Added the following alert:**\n{}".format(notification_to_str(new_notification))

def remove_notification(num,user):
	user_path = get_user_path(user)
	if user_path is None:
		return "User not found."

	if not is_integer(num):
		return "That's not a valid integer."
	num = int(num)
	notifications = read_notifications(user)
	if not num <= len(notifications) or not num > 0:
		return "Not a valid selection."
	
	removed_notification = notifications.pop(num-1)
	settings_io.write_config_from_list(user_path,notifications)

	return "**Deleted the following alert:**\n{}".format(notification_to_str(removed_notification))

def read_notifications(user):
	user_path = get_user_path(user)
	if user_path is None:
		return None
	return settings_io.read_config_as_list(user_path)

def list_notifications(user):
	notifications = read_notifications(user)
	if notifications is None:
		return "Could not find alerts for {}".format(str(user))
	notif_str = "You have the following alerts:\n"
	i = 1
	for notification in notifications:
		notif_str += "**Alert #{}:**\n".format(i) + notification_to_str(notification)
		i += 1
	return notif_str

def undo_last_change(user):
	user_path = get_user_path(user)
	if user_path is None:
		return "User not found."
	if settings_io.revert_previous_write(user_path):
		return "Sucessfully undid previous change."
	else:
		return "Unable to undo last change."
	return

def transform_user_to_sub(notification,user):
	'''converts a notification of type (sub,type,query) to (sub,user,type,query)'''
	notification = notification.copy()
	notification['user'] = os.path.basename(user)
	return notification

def get_all_notifications(path='users'):
	notification_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f))]
	notification_dict = {}
	for file in notification_files:
		curr_user = read_notifications(file)
		for curr_entry in curr_user:
			if curr_entry['sub'] in notification_dict:
				notification_dict[curr_entry['sub']].append(transform_user_to_sub(curr_entry,file))
			else:
				notification_dict[curr_entry['sub']] = [transform_user_to_sub(curr_entry,file)]
	return notification_dict

def get_valid_users():
	USERS_FILE = 'users.ini'
	config_dict = settings_io.read_config_as_dict(USERS_FILE)
	users_list = []
	for key in config_dict:
		# add validation here? e.g. require that channel id specified
		users_list.append(key)
	return users_list

def get_user_channel_id(user):
	USERS_FILE = 'users.ini'
	values = ['channel_id']
	return settings_io.read_auth(USERS_FILE,user,values)['channel_id']

def add_user(user_id,channel_id):
	USERS_FILE = 'users.ini'
	user_dict = {'channel_id':channel_id}
	settings_io.add_named_config_item(USERS_FILE,user_dict,user_id)