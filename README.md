reddit-discord-notifier
=====
Sends you messages on Discord about new Reddit posts matching criteria.  

Dependencies
-----
Runs on python3. Uses praw for Reddit access and discord.py for Discord access.  

Setting up
-----
Move `auth.ini` from TEMPLATE folder to base folder and put Reddit and Discord information provided fields. `admin` field allows you to `!stop` the script nicely.  
If desired, create a text file called `allowed_subreddits` and list subreddits which users are allowed to add, one per line.  
Requires Reddit API access in the form of a personal use script [(go here)](https://www.reddit.com/prefs/apps), and Discord bot API access [(go here, add a bot to get a token)](https://discordapp.com/developers/applications/).  

Running
-----
`python3 reddit-discord-bot.py`  

Usage
-----
Make sure your bot is in a server so you can message it. Private message it `!help` to get a list of commands. Note that commands besides `!help` will not work before you `!initialize`.  
