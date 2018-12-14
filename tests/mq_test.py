import telegram.bot
from telegram.ext import messagequeue as mq


class MQBot(telegram.bot.Bot):
    '''A subclass of Bot which delegates send method handling to MQ'''
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass
        super(MQBot, self).__del__()

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        '''Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments'''
        return super(MQBot, self).send_message(*args, **kwargs)


if __name__ == '__main__':
    from telegram.ext import MessageHandler, Filters
    from telegram.utils.request import Request
    import os
    token = '745952950:AAGBEaWoSk3awNbtn63bZa7vxFjrubBDS0A'
    # for test purposes limit global throughput to 3 messages per 3 seconds
    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    # set connection pool size for bot 
    request = Request(con_pool_size=8)
    testbot = MQBot(token, request=request, mqueue=q)
    upd = telegram.ext.updater.Updater(bot=testbot)

    def reply(bot, update):
        # tries to echo 10 msgs at once
        chatid = update.message.chat_id
        msgt = update.message.text
        print(msgt, chatid)
        for ix in range(20):
            photo_path = '/home/sergazyk/Downloads/2018-10-26_15-18-37.png'
            with open(photo_path, 'rb') as photo:
                bot.send_photo(chat_id=chatid, photo = photo, text='%s) %s' % (ix + 1, msgt))

    hdl = MessageHandler(Filters.text, reply)
    upd.dispatcher.add_handler(hdl)
    upd.start_polling()