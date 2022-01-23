import asyncio
from datetime import datetime,timedelta
import os
from contextlib import suppress

import discord_io
import data_io
import reddit_io as rdt

import logging
from logging.handlers import TimedRotatingFileHandler

def get_main_logger():
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')

    handler = TimedRotatingFileHandler(
        os.path.join(log_dir,'main.log'),
        when="midnight", interval=1
    )
    handler.setFormatter(formatter)
    handler.suffix = "%Y%m%d"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger

async def check_notifications_periodically(client, logger, LAST_CHECKED):
    '''Every 60 seconds + run time, checks notifications. Meant to run in an event loop.'''
    data_io.do_startup_routine()
    await client.wait_until_ready()
    praw_instance = rdt.get_praw_instance(client.AUTH['reddit api'])

    end_time = datetime.utcnow() - timedelta(minutes=1)

    while not (client.RESTART_FLAG or client.EXIT_FLAG):
        # wait for client to be open if no flags are set
        if (datetime.utcnow() - end_time).seconds < 60 or (
                client.is_closed() and not (client.RESTART_FLAG or client.EXIT_FLAG)):
            await asyncio.sleep(1)
            continue

        end_time = datetime.utcnow()
        try:
            all_notifications = data_io.get_all_notifications()  # note that this is a dictionary
            for curr_sub in all_notifications:
                to_send = False
                try:
                    if curr_sub not in LAST_CHECKED:
                        LAST_CHECKED[curr_sub] = datetime.utcnow() - timedelta(minutes=1)
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
            logger.info("Checked posts until {}".format(end_time.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception:
            logger.exception("Issue checking notifications.")

    logger.info("Exit or restart flag found, closing notification checking loop.")
    return

if __name__ == "__main__":
    log_dir = 'logs/'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = get_main_logger()

    LAST_CHECKED = {}

    client = None
    loop = None

    while client is None or not client.EXIT_FLAG or client.RESTART_FLAG:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = discord_io.PMClient(logger)
            notif_task = loop.create_task(check_notifications_periodically(client, logger, LAST_CHECKED))
            loop.run_until_complete(client.start())
        except Exception as e:
            logger.exception("Discord bot exited with an exception. Restarting, probably.")
        finally:
            if not (client.RESTART_FLAG or client.EXIT_FLAG):
                client.RESTART_FLAG = True  # the client exited for some unknown reason, so restart

            if not client.is_closed():
                logger.info("Closing client.")
                loop.run_until_complete(client.close())

            logger.info("Closing loop.")
            notif_task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(notif_task)
            loop.close()

    logger.info("Reached end of program.")
