import pickle
from multiprocesing import Queue, Process
from vision.photo_analysis import VectorExtractor
from db import meta_db, vector_db
import settings

class VisionWorker:
    def __init__(self):
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.process = Process(target=self.work, args=(task_queue, done_queue))
        self.process.start()

    def work(self, task_queue, done_queue):
        recognition_model_path = settings.recognition_model_path
        ssh_model_path = settings.ssh_model_path
        mtcnn_model_path = settings.mtcnn_model_path
        scales = settings.sacles
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
    '''
        Bot frontend for telegram, entrypoint
    '''
    def __init__(self):
        pass

    def message_handler(self):
        pass

class Bot:
    '''
        Bot logic
    '''
    def __init__(self, info_db_path, faces_db_path, photo_db_path, frontend):
        self.db = meta_db.MetaDB(info_db_path)
        self.faces_db = vector_db.FaissEngine()
        self.faces_db.load(faces_db_path)
        self.photo_db = vector_db.FaissEngine()
        self.photo_db.load(photo_db_path)
        self.vision_worker = VisionWorker()
        self.write_worker = Process(target=self.work, args=(vision_worker))
        self.write_worker.start()
        self.frontend = frontend
        self.frontend.set_photo_handler(posted_photo)

    def photo_handler(self, chat_id, file_path):
        if self.db.get_user(chat_id) is None:
            user_id = self.db.new_user(chat_id)
            photo_id = self.db.new_photo(user_id, file_path)
            self.db.set_avatar(user_id, photo_id)

        self.vision_worker.put_task(photo_id, file_path)

    def work(self, vision_worker):
        while True:
            photo_id, vectors = vision_worker.get_done_task()
            user_id = self.db.get_user_by_photo(photo_id)
            chat_id = self.db.get_chat(user_id)

            if self.db.get_avatar(user_id) == photo_id:
                if len(vectors) == 0:
                    self.frontend.send_message(chat_id, settings.texts['bad_selfie'])
                    break

                similar_faces = self.faces_db.range_search(vectors[0], strong_verification_threshold)
                if len(similar_faces) > 0:


                vector_id = self.faces_db.add(vectors[0]) # assuming faces sorted by area on photo
                self.db.set_vector(user_id, vector_id)

            else:
