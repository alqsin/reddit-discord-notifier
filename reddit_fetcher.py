import praw
from datetime import datetime, timedelta
from time import strftime
import re
import settings_io
import shlex  # for splitting with quoted substring
import os  # for checking if there is an allowed subreddits file

import logging
logger = logging.getLogger()

class RedditPost:
    def __init__(self,post_id,post_title,post_time,post_url,post_author):
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
    '''Converts UTC timestamp to a readable time (still in UTC)'''
    return datetime.utcfromtimestamp(timestamp_utc)

def read_reddit_auth():
    '''Reads reddit auth into dictionary with keys corresponding to praw values.
    Used when praw instance is not provided to function.'''
    reddit_auth = settings_io.Auth()
    return reddit_auth['reddit api']

def validate_search_query(search_query):
    '''Checks if search_query is valid by performing test search.'''
    try:
        match_string(search_query,"this is a test")
    except Exception:
        return False
    return True

def split_query(search_query):
    '''Uses shlex to split a search query. Single quotes are 'ignored' as quotes.
    Comments are allowed (in case someone wants to comment on a particular query I guess???).'''
    search_query = search_query.strip()
    s = shlex.shlex(search_query)
    s.quotes = '"'
    s.whitespace_split = True
    return list(s)

def parse_search_query(search_query):
    '''Converts a search query into a list of + and - words to match (either positively or negatively).'''
    search_word_list = split_query(search_query)  # uses shlex library, be careful here
    positive_matches = []
    negative_matches = []
    for word in search_word_list:
        if word[0] == '-':
            negative_matches.append(r'(?<!\w)' + word[1:] + r'(?!\w)') #lookbehind and lookahead to make sure word is not surrounded by any alphanumeric characters
        else:
            positive_matches.append(r'(?<!\w)' + word + r'(?!\w)')
    return (positive_matches,negative_matches)

def match_string(search_query,text):
    '''Given a search query, searches text and returns true if matching. Ignores case.'''
    (positive_matches,negative_matches) = parse_search_query(search_query)
    for val in negative_matches:
        pattern = re.compile(val,re.IGNORECASE)
        if pattern.search(text) is not None:
            return False
    for val in positive_matches:
        pattern = re.compile(val,re.IGNORECASE)
        if pattern.search(text) is None:
            return False
    return True

def get_reddit_posts(subreddit_name,reddit,start_time,end_time):
    '''Returns posts in /r/subreddit_name posted after cutoff_time.
    reddit is an instance of praw with authorization included.'''
    NUMBER_NEW_TO_GET = 10  # assuming bot checks once every minute, hopefully there are no more than 10 posts per minute

    subreddit = reddit.subreddit(subreddit_name)

    new_submissions = []

    for submission in subreddit.new(limit=NUMBER_NEW_TO_GET):
        post_time = get_time_from_stamp(submission.created_utc) #submission.created_utc returns unix timestamp in utc
        post_title = submission.title
        post_id = submission.fullname
        post_author = submission.author
        post_url = 'https://www.reddit.com' + submission.permalink  # consider checking for presence of https in case they change how this works in future
        # consider adding score, body, etc.
        current_post = RedditPost(post_id=post_id,post_title=post_title,post_time=post_time,post_url=post_url,post_author=post_author)
        if (post_time) > end_time:
            continue
        elif (post_time < start_time): #doesn't bother parsing if submission is too old
            break
        else:
            new_submissions.append(current_post)
    return new_submissions

def check_one_subreddit(subreddit_name,notifications,reddit,start_time,end_time):
    '''Checks subreddit /r/subreddit_name for each notification in notifications.
    Reddit is a praw instance, start and end times indicate the interval to check.'''
    new_posts = get_reddit_posts(subreddit_name,reddit,start_time,end_time)
    notifications_to_send = []
    for post in new_posts:
        # TODO: iterate through users rather than through a list of all notifications
        for notification in notifications:
            curr_match = False
            if notification['type'] == 'title':
                post_val_to_search = post.post_title
                if match_string(notification['query'],post_val_to_search):
                    curr_match = True
            elif notification['type'] == 'author':
                post_val_to_search = post.post_author.name
                if notification['query'].lower() == post_val_to_search.lower():
                    curr_match = True
            else:
                raise ValueError("Invalid search type for subreddit {}".format(notification['sub']))
            if curr_match:
                logger.info("Found notification for post {}.".format(post.post_title))
                tuple_to_add = (notification['user'],post)
                if tuple_to_add not in notifications_to_send:
                    logger.info("Adding notification for {} to queue.".format(notification['user']))
                    notifications_to_send.append(tuple_to_add)
    return notifications_to_send  # note that this is an array of pairs of type (str,RedditPost)

def get_praw_instance(reddit_auth):
    '''Uses auth.ini to create an instance of praw.'''
    return praw.Reddit(**reddit_auth)

def validate_subreddit(subreddit_name,reddit=get_praw_instance(read_reddit_auth())):
    '''Checks if subreddit is part of subreddit list. If there is no list,
    instead checks that a subreddit exists and has at least 10 posts. 
    Second function will not work if reddit is down.'''
    allowed_subreddits_file = 'allowed_subreddits'
    
    if not isinstance(subreddit_name, str):
        return False

    if not os.path.exists(allowed_subreddits_file):
        try:
            i = 1
            posts = reddit.subreddit(subreddit_name).new(limit=10)
            for _ in posts:
                i += 1
            if i < 10:
                return False
            return True
        except Exception:
            return False
    if subreddit_name in settings_io.open_file_as_list(allowed_subreddits_file):
        return True
    return False

def validate_author(author):
    '''Checks if an author is valid.'''
    if author is None:
        return False
    if not isinstance(author, str):
        return False
    if ' ' in author:
        return False

    user_rx = re.compile(r'\A[\w-]+\Z', re.UNICODE)  # from reddit-archive github
    if not user_rx:
        return False
    return True
