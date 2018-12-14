import pickle
from multiprocessing import Queue, Process
from vision.photo_analysis import VectorExtractor
from db import meta_db, vector_db
import settings

import logging
import uuid
import time
import os
import threading
import glob

import telegram
from telegram.utils import request
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request

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

class VisionWorker:
    def __init__(self):
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.thread = threading.Thread(target=self.work, args=(self.task_queue, self.done_queue))
        self.thread.daemon = True
        self.thread.start()

    def work(self, task_queue, done_queue):
        recognition_model_path = settings.recognition_model_path
        ssh_model_path = settings.ssh_model_path
        mtcnn_model_path = settings.mtcnn_model_path
        scales = settings.scales
        detection_threshold = settings.detection_threshold
        extractor = VectorExtractor(recognition_model_path, ssh_model_path,
                    mtcnn_model_path, scales, detection_threshold)

        while True:
            photo_id, file_path = task_queue.get()

            vectors = extractor.retrieve(file_path)
            
            self.done_queue.put((photo_id, vectors))

    def put_task(self, photo_id, file_path):
        self.task_queue.put((photo_id, file_path))

    def get_done_task(self):
        return self.done_queue.get()

class TelegramBot:
    """
        Bot frontend for telegram, entrypoint
    """
    def __init__(self, distributor, photo_storage_path):

        request = Request(con_pool_size=8)
        q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
        bot = MQBot(settings.token, request=request, mqueue=q)
        self.bot = bot
        

        self.updater = Updater(token = settings.token, workers = 3)
        dispatcher = self.updater.dispatcher

        distributor.set_frontend(self)

        def start(bot, update):
            bot.send_message(chat_id=update.message.chat_id, text=settings.texts['hello'])

        def handle_text_message(bot, update):
            bot.send_message(chat_id=update.message.chat_id, text="Send me photos, not text. I am not Siri")


        def handle_photo(bot, update):
            file_id = update.message.photo[-1]
            newFile = bot.get_file(file_id)
            unique_str = photo_storage_path + str(uuid.uuid4()) + '.jpg'
            newFile.download(unique_str)
            distributor.photo_handler(update.message.chat_id, unique_str,
                [str(update.message.from_user.username), update.message.from_user.first_name, str(update.message.from_user.first_name)])

        self.distributor = distributor

        start_handler = CommandHandler('start', start)
        dispatcher.add_handler(start_handler)

        handle_photo_handler = MessageHandler(Filters.photo, handle_photo)
        dispatcher.add_handler(handle_photo_handler)



    def manual_add(self, chat_id, path):
        print(glob.glob(path))
        for image_path in glob.glob(path):
            self.distributor.photo_handler(chat_id, image_path, ['SergazyK'])

    def send_message(self, chat_id, text, retries = 10):
        if retries == 0:
            return

        try:
            self.bot.send_message(chat_id=chat_id, text=text)
            
        except Exception as e:
            print(e)
            print('retrying to send')
            threading.Timer(1*2**(10 - retries), self.send_message, [chat_id, text, retries - 1]).start()

    def send_photo(self, photo_path, chat_id, text, retries = 10):
        if retries == 0:
            return
        
        try :
            with open(photo_path, 'rb') as photo:
                self.bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
                

        except Exception as e:
            print(e)
            print('retrying to send')
            threading.Timer(1*2**(10 - retries), self.send_photo, [photo_path, chat_id, text, retries - 1]).start()
            

    def start(self):
        self.updater.start_polling()


class Distributor:
    """
        Bot logic
    """
    def __init__(self, info_db_path, faces_db_path, photo_db_path):
        self.db = meta_db.DumbDB(info_db_path)
        self.db.load()
        self.faces_db = vector_db.FaissEngine()
        self.faces_db.load(faces_db_path)
        self.photo_db = vector_db.FaissEngine()
        self.photo_db.load(photo_db_path)
        self.vision_worker = VisionWorker()
        self.last_save = time.time()
        self.write_worker = threading.Thread(target=self.work, args=(self.vision_worker, ))
        self.write_worker.start()
        

    def set_frontend(self, frontend):
        self.frontend = frontend

    def photo_handler(self, chat_id, file_path, username_firstname):
        user_id = None

        if self.db.get_user(chat_id) == -1:
            username = 'Unknown'
            for cand in username_firstname[::-1]:
                if len(cand) > 1:
                    username = cand

            user_id = self.db.new_user(chat_id, username)
        else:
            user_id = self.db.get_user(chat_id)

        photo_id = self.db.new_photo(user_id, file_path)

        self.vision_worker.put_task(photo_id, file_path)

    def send_updates(self, user_id, vector):
        indexes = self.photo_db.range_search(vector, settings.strong_verification_threshold)
        sent_photos = set()
        for index in indexes:
            photo_id = self.db.get_photo_by_vector(index) 
            self.db.add_tag_to_photo(photo_id, user_id)
            if photo_id not in sent_photos:
                self.send_photo(photo_id, user_id)
                sent_photos.add(photo_id)

        return

    def send_photo(self, photo_id, tagged_user_id):
        sender_id = self.db.get_sender(photo_id)
        tags = list(self.db.get_tags(photo_id))
        tag_string = 'Sent by @'
        tag_string += self.db.get_username(sender_id)
        tag_string += '\nTagged:'

        for user_id in tags:
            tag_string += ' @' + self.db.get_username(user_id)
        
        self.frontend.send_photo(self.db.get_photo_path(photo_id),
            self.db.get_chat(tagged_user_id), tag_string)

    def work(self, vision_worker):
        while True:
            if time.time() - self.last_save > 1:
                self.db.dump()
                self.faces_db.dump()
                self.photo_db.dump()
                self.last_save = time.time()

            photo_id, vectors = vision_worker.get_done_task()
            user_id = self.db.get_sender(photo_id)
            chat_id = self.db.get_chat(user_id)


            if self.db.get_vector(user_id) == -1:
                if len(vectors) == 0:
                    self.frontend.send_message(chat_id, settings.texts['bad_selfie'])
                    break

                similar_faces = self.faces_db.range_search(vectors[0], settings.strong_verification_threshold)
                if len(similar_faces) > 0:
                    self.frontend.send_message(chat_id, settings.texts['auth_failed'])
                    break

                vector_id = self.faces_db.add(vectors[0]) # assuming faces sorted by area on photo
                self.db.set_vector(user_id, vector_id)
                self.frontend.send_message(chat_id, settings.texts['accepted_selfie'])

                self.send_updates(user_id, vectors[0])
            
            else:
                recognized = []
                for vector in vectors:
                    vector_id = self.photo_db.add(vector)
                    self.db.add_vector(photo_id, vector_id)
                    
                    distances, indexes = self.faces_db.search(vector, 1)
                    if len(indexes) > 0:
                        if distances[0] < settings.strong_verification_threshold:
                            face_vector_id = indexes[0][0]
                            tagged_id = self.db.get_user_by_vector(face_vector_id)
                            recognized.append((photo_id, tagged_id))
                            self.db.add_tag_to_photo(photo_id, tagged_id)
                
                for photo_id, tagged_id in recognized:
                    if tagged_id != user_id:
                        self.send_photo(photo_id, tagged_id)
