#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import threading
from multiprocessing import Process

import yaml
import datetime
import logging

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Application
from telegram.error import BadRequest
import webserver

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

class HomeBot:
    def __init__(self):
        self.config = None
        self.bot = None
        self.loop = None
        self.exit = threading.Event()

    @staticmethod
    def assemble_inline_buttons(button_data):
        buttons = []
        for row_data in button_data:
            row = []
            for button_data in row_data:
                button = InlineKeyboardButton(
                    button_data['text'],
                    callback_data=button_data['data'],
                )
                row.append(button)
            buttons.append(row)
        return InlineKeyboardMarkup(buttons)

    def dispatch_send_message(self, message, update_message_id=None):
        self.loop.run_until_complete(self.send_message(message, update_message_id))

    async def send_message(self, message, update_message_id=None):
        recipient_id = self.config['target_chat_id']
        if isinstance(message, dict):
            buttons = None
            if message.get('buttons'):
                buttons = self.assemble_inline_buttons(message['buttons'], key)
            if 'photo' in message:
                if update_message_id is not None:
                    await self.bot.edit_message_media(
                        chat_id=recipient_id,
                        message_id=update_message_id,
                        reply_markup=buttons,
                        media=InputMediaPhoto(
                            open(message['photo'], 'rb'),
                            caption=message.get('message'),
                            parse_mode=message.get('parse_mode')
                        )
                    )
                else:  # new photo
                    await self.bot.send_photo(recipient_id,
                                        open(message['photo'], 'rb'),
                                        caption=message.get('message'),
                                        reply_markup=buttons,
                                        parse_mode=message.get('parse_mode'))
            else:
                if update_message_id is not None:
                    await self.bot.edit_message_text(
                        text=message['message'],
                        reply_markup=buttons,
                        chat_id=recipient_id,
                        message_id=update_message_id,
                        parse_mode=message.get('parse_mode')
                    )
                else:
                    await self.bot.send_message(recipient_id,
                                          message['message'],
                                          reply_markup=buttons,
                                          parse_mode=message.get('parse_mode'))
        else:
            if update_message_id is not None:
                await self.bot.edit_message_text(
                    text=message,
                    chat_id=recipient_id,
                    message_id=update_message_id
                )
            else:
                await self.bot.send_message(recipient_id, message)

    # Help command handler
    async def handle_help(self, update, context):
        """Send a message when the command /help is issued."""
        helptext = "This bot will relay form submissions from a specific Google form to the configured group chat. You can't really do anything else with it."

        await update.message.reply_text(helptext, parse_mode="Markdown")

    # Error handler
    async def handle_error(self, update, context):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)
        if self.config['debug']:
            import traceback
            traceback.print_exception(context.error)
    
    def start_dp_on_thread(self, dp):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        dp.run_polling()

    def run(self, opts):
        with open(opts.config, 'r') as configfile:
            config = yaml.load(configfile, Loader=yaml.SafeLoader)

        self.config = config
        if 'debug' not in config:
            config['debug'] = False
        if config['debug']:
            logger.info("Debug mode is ON")

        """Start the bot."""
        # Create the EventHandler and pass it your bot's token.
        dp = Application.builder().token(config['token']).concurrent_updates(True).build()
        self.bot = dp.bot
        self.loop = asyncio.get_event_loop()

        dp.add_handler(CommandHandler("help", self.handle_help))

        dp.add_error_handler(self.handle_error)

        webserver.init(self.dispatch_send_message, self.config)
        # Start the Bot

        t = Process(target=webserver.run)
        t.start()

        dp.run_polling()

        self.exit.set()
        t.terminate()
        t.join()


def main(opts):
    HomeBot().run(opts)


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-c', '--config', dest='config', default='config.yml', type='string',
                      help="Path of configuration file")
    (opts, args) = parser.parse_args()
    main(opts)
