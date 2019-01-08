reddit-discord-notifier
=====
Sends you messages on Discord about new Reddit posts matching criteria.  

Dependencies
-----
Runs on python3. Uses praw for Reddit access and discord.py for Discord access.  

Setting up
-----
Set up Reddit "personal use script" API access [(go here)](https://www.reddit.com/prefs/apps), and Discord bot API access [(go here, add a bot to get a token)](https://discordapp.com/developers/applications/).  
Move `auth.ini` from `TEMPLATE` folder to `notifier` folder and replace information in the fields provided. Note that `admin` field allows you to `!stop` the script nicely.  
If desired, create a text file called `allowed_subreddits` and list subreddits which users are allowed to add, one per line.  

Running
-----
`python3 bot.py`  

Usage
-----
Make sure your bot is in a server so you can message it. Private message it `!help` to get a list of commands. Commands besides `!help` will not work before you `!initialize`.  
