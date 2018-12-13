import pickle
from multiprocessing import Queue, Process
from vision.photo_analysis import VectorExtractor
from db import meta_db, vector_db
import settings

import logging
import uuid
import time
import os

import telegram
from telegram.utils import request
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext.dispatcher import run_async


class VisionWorker:
    def __init__(self):
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.process = Process(target=self.work, args=(self.task_queue, self.done_queue))
        self.process.start()

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

        bot = telegram.Bot(token=settings.token)
        self.bot = bot
        request.CON_POOL_SIZE = 10

        self.updater = Updater(token = settings.token, workers = 10)
        dispatcher = self.updater.dispatcher

        distributor.set_frontend(self)

        def start(bot, update):
            bot.send_message(chat_id=update.message.chat_id, text=settings.texts['hello'])

        def handle_text_message(bot, update):
            bot.send_message(chat_id=update.message.chat_id, text="Send me photos, not text. I am not Siri")


        def handle_photo(bot, update):
            file_id = update.message.photo[-1]
            newFile = bot.get_file(file_id)
            unique_str = photo_storage_path + str(uuid.uuid4())
            newFile.download(unique_str)
            os.rename(unique_str, unique_str + '.jpg')
            unique_str += '.jpg'
            distributor.photo_handler(update.message.chat_id, unique_str,
                [str(update.message.from_user.username), update.message.from_user.first_name, str(update.message.from_user.first_name)])


        start_handler = CommandHandler('start', start)
        dispatcher.add_handler(start_handler)

        handle_photo_handler = MessageHandler(Filters.photo, handle_photo)
        dispatcher.add_handler(handle_photo_handler)


    def send_message(self, chat_id, text, retries = 10):
        if retries == 0:
            return
        try:
            self.bot.send_message(chat_id=chat_id, text=text)
        except:
            time.sleep(1*2**(10 - retries))
            self.send_message(chat_id, text, retries = retries - 1)

    def send_photo(self, photo_path, chat_id, text, retries = 10):
        if retries == 0:
            return
        try:
            with open(photo_path, 'rb') as photo:
                self.bot.send_photo(chat_id=chat_id, photo=photo, caption=text)
        except:
            time.sleep(3*2**(10 - retries))
            self.send_photo(photo_path, chat_id, text, retries - 1)

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
        self.write_worker = Process(target=self.work, args=(self.vision_worker, ))
        self.write_worker.start()

    def set_frontend(self, frontend):
        self.frontend = frontend

    def photo_handler(self, chat_id, file_path, username_firstname):
        user_id = None

        if self.db.get_user(chat_id) is None:
            username = 'Unknown'
            for cand in username_firstname[::-1]:
                if len(cand) > 1:
                    username = cand
            user_id = self.db.new_user(chat_id, username)
        else:
            user_id = self.db.get_user(chat_id)

        photo_id = self.db.new_photo(user_id, file_path)

        if self.db.get_vector(user_id) is None:
            self.db.set_avatar(user_id, photo_id)

        self.vision_worker.put_task(photo_id, file_path)

    def send_updates(self, user_id, vector):
        indexes = self.photo_db.range_search(vector, settings.strong_verification_treshold)
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
        tag_string = 'Sent by'
        tag_string += self.db.get_username(sender_id)
        tag_string += '\n Tagged:'

        for user_id in tag_string:
            tag_string += ' ' + self.db.get_username(user_id)
        
        self.frontend.send_photo(self.db.get_photo_path(photo_id),
            self.db.get_chat(tagged_user_id), tag_string)

    def work(self, vision_worker):
        while True:
            photo_id, vectors = vision_worker.get_done_task()
            user_id = self.db.get_sender(photo_id)
            chat_id = self.db.get_chat(user_id)


            if self.db.get_avatar(user_id) == photo_id:
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
                    
                    indexes, distances = self.face_db.search(vector, 1)
                    if len(indexes) > 0:
                        if distances[0] > settings.strong_verification_treshold:
                            face_vector_id = indexes[0]
                            tagged_id = self.db.get_user_by_vector(face_vector_id)
                            recognized.append((photo_id, tagged_id))
                            self.db.add_tag_to_photo(photo_id, tagged_id)
                
                for photo_id, tagged_id in recognized:
                    if tagged_id != user_id:
                        self.send_photo(photo_id, tagged_id)
