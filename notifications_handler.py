import settings_io
import os
import reddit_fetcher as rdt

def is_integer(x):
    '''Returns true if x can be cast to integer; else returns False.'''
    try:
        int(x)
    except Exception:
        return False
    return True

def do_startup_routine(path='users'):
    '''Creates users folder if it doesn't exist.'''
    if not os.path.exists(path):
        os.makedirs(path)

def notification_to_str(notification):
    '''Converts a notification dictionary into a string.'''
    return "Subreddit: /r/{}\nType: {}\nQuery: {}\n".format(notification['sub'],notification['type'],notification['query'])

def get_user_path(user,path='users'):
    '''Joins path to users folder with user.'''
    return os.path.join(path,user)

def add_notification(text,user_id):
    '''Adds notification to user with id user_id from text.
    Format for notification text should be [subreddit] [type] [search query].'''
    split_text = text.split(' ',2)
    if len(split_text) != 3:
        return "Invalid alert format, please try again."
    
    sub = split_text[0]
    query_type = split_text[1]
    query = split_text[2]

    if not rdt.validate_subreddit(sub):
        return ("Subreddit is either invalid or not allowed (or Reddit is down).")
    if not (query_type == 'title' or query_type == 'author'):
        return "Query type must be title or author."
    if query_type == 'title' and not rdt.validate_search_query(query):
        return "Not a valid search query."
    elif query_type == 'author' and not rdt.validate_author(query):
        return "Not a valid reddit username."

    new_notification = {'sub':split_text[0],'type':split_text[1],'query':split_text[2]}
    settings_io.add_config_item(get_user_path(user_id),new_notification)

    return "**Added the following alert:**\n{}".format(notification_to_str(new_notification))

def remove_notification(num,user_id):
    '''Removes notification number num from list of user with id user_id.'''
    if not is_integer(num):
        return "That's not a valid integer."
    num = int(num)
    notifications = read_notifications(user_id)
    if not num <= len(notifications) or not num > 0:
        return "Not a valid selection."
    
    removed_notification = notifications.pop(num-1)
    settings_io.write_config_from_list(get_user_path(user_id),notifications)

    return "**Deleted the following alert:**\n{}".format(notification_to_str(removed_notification))

def read_notifications(user_id):
    '''Returns notifications of user with id user_id, as a list of notification dicts.'''
    user_path = get_user_path(user_id)
    return settings_io.read_config_as_list(user_path)

def list_notifications(user_id):
    '''Outputs notifications of user with id user_id, as text.'''
    notifications = read_notifications(user_id)
    if not notifications:
        return "Could not find alerts for user."
    notif_str = "You have the following alerts:\n"
    i = 1
    for notification in notifications:
        notif_str += "**Alert #{}:**\n".format(i) + notification_to_str(notification)
        i += 1
    return notif_str

def append_user_to_dict(notification,user_path):
    notification = notification.copy()
    notification['user'] = os.path.basename(user_path)
    return notification

def get_all_notifications(path='users'):
    '''Goes through folder path and gets every notification. Also adds user as an entry to the dictionary.'''
    if not os.path.isdir(path):
        # this shouldn't happen, as path is created on startup
        return {}
    notification_dict = {}
    users = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f))]
    for user in users:
        curr_user = read_notifications(user)
        for curr_entry in curr_user:
            if curr_entry['sub'] in notification_dict:
                notification_dict[curr_entry['sub']].append(append_user_to_dict(curr_entry,user))
            else:
                notification_dict[curr_entry['sub']] = [append_user_to_dict(curr_entry,user)]
    return notification_dict

def validate_user(user_id):
    '''Checks if user is initialized.'''
    if os.path.exists(get_user_path(user_id)):
        return True
    return False

def initialize_user(user_id):
    '''Initializes user.'''
    if validate_user(user_id):
        return "You already have a list!"
    else:
        try:
            open(get_user_path(user_id),'a').close()
            return "Successfully initialized!"
        except Exception:
            return "Something went wrong with initialization, please contact my owner."

def deinitialize_user(user_id):
    '''Deletes user's list.'''
    try:
        os.remove(get_user_path(user_id))
        return "Removed your list!"
    except Exception:
        return "Something went wrong with removal, please contact my owner."
