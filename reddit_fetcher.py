import praw
from datetime import datetime, timedelta
from time import strftime
import re
import settings_io
import shlex  # for splitting with quoted substring

import logging
log = logging.getLogger()

class RedditPost:
	'''structure of a reddit post'''
	def __init__(self,post_id,post_title,post_time,post_url,post_author):  # wow this is so wordy
		self.post_id = post_id
		self.post_title = post_title
		self.post_time = post_time
		self.post_url = post_url
		self.post_author = post_author
	def __eq__(self,other):
		return self.post_id == other.post_id
	def __str__(self):
		return "{}\n{}\n".format(self.post_title,self.post_url)

def get_time_from_stamp(timestamp_utc):
	'''converts UTC timestamp to a readable time (still in UTC)'''
	return datetime.fromtimestamp(timestamp_utc)

def read_reddit_auth():
	'''reads reddit auth into dictionary with keys corresponding to praw values'''
	AUTH_FILE = 'auth.ini'
	AUTH_ENTRY = 'reddit api'
	AUTH_VALUES = ['client_id','client_secret','username','password','user_agent']
	return settings_io.read_auth(AUTH_FILE,AUTH_ENTRY,AUTH_VALUES)

def parse_search_query(search_query):
	'''converts a search query into a list of + and - words to match'''
	search_query = search_query.strip()
	search_word_list = shlex.split(search_query)  # uses shlex library, be careful here
	positive_matches = []
	negative_matches = []
	for word in search_word_list:
		if word[0] == '-':
			negative_matches.append(r'(?<!\w)' + word[1:] + r'(?!\w)') #lookbehind and lookahead to make sure word is not surrounded by any alphanumeric characters
		else:
			positive_matches.append(r'(?<!\w)' + word + r'(?!\w)')
	return (positive_matches,negative_matches)

def match_string(search_query,word):
	'''given a list of regex-compatible strings, searches word and returns true if all strings are matched
	ALWAYS IGNORES CASE, even when trying to search user'''
	(positive_matches,negative_matches) = parse_search_query(search_query)
	for val in negative_matches:
		pattern = re.compile(val,re.IGNORECASE)
		if pattern.search(word) is not None:
			return False
	for val in positive_matches:
		pattern = re.compile(val,re.IGNORECASE)
		if pattern.search(word) is None:
			return False
	return True

def get_reddit_posts(subreddit_name,reddit,start_time,end_time):
	'''returns posts in /r/subreddit_name posted after cutoff_time
	reddit is an instance of praw with authorization included'''
	NUMBER_NEW_TO_GET = 10  # assuming bot checks once every minute, hopefully there are no more than 10 posts per minute

	subreddit = reddit.subreddit(subreddit_name)

	new_submissions = []

	for submission in subreddit.new(limit=NUMBER_NEW_TO_GET):
		post_time = get_time_from_stamp(submission.created_utc) #submission.created returns timestamp in utc
		post_title = submission.title
		post_id = submission.fullname
		post_author = submission.author
		post_url = submission.permalink
		# consider adding score, etc.
		current_post = RedditPost(post_id=post_id,post_title=post_title,post_time=post_time,post_url=post_url,post_author=post_author)
		if (post_time) > end_time:
			continue
		elif (post_time < start_time): #doesn't bother parsing if submission is too old
			break
		else:
			new_submissions.append(current_post)
	return new_submissions

def check_one_subreddit(subreddit_name,notifications,reddit,start_time,end_time):
	new_posts = get_reddit_posts(subreddit_name,reddit,start_time,end_time)
	notifications_to_send = []
	for post in new_posts:
		for notification in notifications:
			curr_match = False
			if notification['type'] == 'title':
				post_val_to_search = post.post_title
				if match_string(notification['query'],post_val_to_search):
					curr_match = True
			elif notification['type'] == 'author':
				post_val_to_search = post.post_author.name
				if notification['query'].lower() == post_val_to_search:
					curr_match = True
			else:
				raise ValueError("Invalid search type for subreddit {}".format(notification.subreddit_name))
			if curr_match:
				logging.info("Found notification for post {}".format(post.post_title))
				tuple_to_add = (notification['user'],post)
				if tuple_to_add not in notifications_to_send:
					notifications_to_send.append(tuple_to_add)
	return notifications_to_send  # note that this is an array of pairs of type (str,RedditPost)

def get_praw_instance():
	return praw.Reddit(**read_reddit_auth())

def validate_subreddit(subreddit_name,reddit=get_praw_instance()):
	try:
		i = 1
		posts = reddit.subreddit(subreddit_name).new(limit=10)
		for post in posts:
			i += 1
		if i < 10:
			return False
		return True
	except:
		return False
