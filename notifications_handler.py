import settings_io
import os
import reddit_fetcher as rdt

def is_integer(x):
	'''Returns true if x can be cast to integer; else returns False.'''
	try:
		int(x)
	except:
		return False
	return True

def do_startup_routine(path='users'):
	if not os.path.exists(path):
		os.makedirs(path)

def notification_to_str(notification):
	return "Subreddit: /r/{}\nType: {}\nQuery: {}\n".format(notification['sub'],notification['type'],notification['query'])

def get_user_path(user,path='users'):
	user_path = os.path.join(path,user)
	if not os.path.exists(user_path):
		return None
	return user_path

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
		return ("Invalid subreddit (or Reddit is down and validation failed).")
	if not (query_type == 'title' or query_type == 'author'):
		return "Query type must be title or author."
	if not rdt.validate_search_query(query):
		return "Not a valid search query."

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
	notifications = read_notifications(user_path)
	if not num <= len(notifications) or not num > 0:
		return "Not a valid selection."
	
	removed_notification = notifications.pop(num-1)
	settings_io.write_config_from_list(user_path,notifications)

	return "**Deleted the following alert:**\n{}".format(notification_to_str(removed_notification))

def read_notifications(user_path):
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

def get_all_notifications(path='users'):
	if not os.path.isdir(path):
		# this shouldn't happen, as path is created on startup
		return {}
	notification_dict = {}
	users = [f for f in os.listdir(path) if not os.path.isfile(os.path.join(path,f))]
	for user in users:
		curr_user = read_notifications(get_user_path(user,path))
		for curr_entry in curr_user:
			if curr_entry['sub'] in notification_dict:
				notification_dict[curr_entry['sub']].append(append_user_to_dict(curr_entry,file))
			else:
				notification_dict[curr_entry['sub']] = [append_user_to_dict(curr_entry,file)]
	return notification_dict

def append_user_to_dict(notification,path_to_user):
	notification = notification.copy()
	notification['user'] = os.path.basename(path_to_user)
	return notification
