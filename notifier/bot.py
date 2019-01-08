import asyncio
from datetime import datetime,timedelta
import os
import time  # for sleeping in body

import discord_io
import data_io
import reddit_io as rdt

import logging
from logging.handlers import TimedRotatingFileHandler

async def check_notifications_periodically(client):
    '''Every 60 seconds + run time, checks notifications. Meant to run in an event loop.'''
    data_io.do_startup_routine()
    await client.wait_until_ready()
    praw_instance = rdt.get_praw_instance(client.AUTH['reddit api'])
    TIMES_CHECKED = 0
    while not (client.RESTART_FLAG or client.EXIT_FLAG):
        # wait for client to be open if no flags are set
        while client.is_closed and not (client.RESTART_FLAG or client.EXIT_FLAG):
            logger.info("Client is closed, waiting 15 seconds.")
            await asyncio.sleep(15)
        end_time = datetime.utcnow()
        try:
            TIMES_CHECKED += 1
            all_notifications = data_io.get_all_notifications()  # note that this is a dictionary
            for curr_sub in all_notifications:
                to_send = False
                try:
                    if curr_sub not in LAST_CHECKED:
                        LAST_CHECKED[curr_sub] = datetime.utcnow() - timedelta(minutes=5)
                    to_send = rdt.check_one_subreddit(curr_sub,all_notifications[curr_sub],praw_instance,LAST_CHECKED[curr_sub],end_time)
                    LAST_CHECKED[curr_sub] = end_time
                except Exception:
                    logger.exception("Failure to check reddit posts for {}.".format(curr_sub))
                if to_send:
                    for (curr_user,curr_post) in to_send:
                        try:
                            await client.message_user(curr_user,"**New reddit post matching your alert!**\n{}".format(str(curr_post)))
                        except Exception:
                            logger.exception("Failed to send notification to user {}.".format(curr_user))
            logger.info("({}) Checked posts until {}".format(TIMES_CHECKED,end_time.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception:
            logger.exception("Issue checking notifications.")
        await asyncio.sleep(60)  # I guess it doesn't matter if it checks exactly every minute
    logger.info("Exit or restart flag found, closing notification checking loop.")
    return

if __name__ == "__main__":
    log_dir = 'logs/'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

    # set main logger
    handler = TimedRotatingFileHandler(
        os.path.join(log_dir,'main.log'),
        when="midnight", interval=1
    )
    handler.setFormatter(formatter)
    handler.suffix = "%Y%m%d"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    LAST_CHECKED = {}

    client = None

    while client is None or not client.EXIT_FLAG or client.RESTART_FLAG:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = discord_io.PMClient(logger)
            loop.create_task(check_notifications_periodically(client))
            loop.run_until_complete(client.start())
        except Exception as e:
            logger.exception("Discord bot exited with an exception. Restarting, probably.")
        if not (client.RESTART_FLAG or client.EXIT_FLAG):
            client.RESTART_FLAG = True  # the client exited for some unknown reason, so restart
        if not client.is_closed:
            logger.info("Closing and restarting client.")
            client.close()
        if not loop.is_closed():
            logger.info("Closing and restarting loop.")
            loop.close()

    logger.info("Reached end of program.")
