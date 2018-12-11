import pickle
from ... import utils
import threading
import logging

class SyncOp(contextlib.ContextDecorator):
    def __init__(self, lock=None, db):
        self.db = db
        if lock:
            self.lock = lock
        else:
            self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        self.db.load()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.dump()
        self.lock.release()

class DumbDB:
    '''
        Dumbest DB engine ever
    '''
    def __init__(self):
        self.db = {'chats': {}, 'users': {}, 'photos': {}, 'photo_vectors': {}, 'user_vectors': {}, 'num_users': 0, 'num_photos': 0}
        self.lock = threading.Lock()
    
    def load(self, load_path = None):
        if load_path is not None:
            self.load_path = load_path

        try:
            self.db = pickle.load(open(self.load_path, 'rb'))
        except:
            logging.error("Couldn't load meta db, starting from scratch")

    def dump(self):
        pickle.dump(self.db, open(self.load_path, 'wb'))

    @SyncOp(self.lock, self)
    def new_user(self, chat_id):
        '''
            create user and return unique id
        '''
        user_id = self.db['num_users']
        self.db['chats'][chat_id] = {'user': user_id}
        self.db['users'][user_id] = {'chat': chat_id, 'avatar': None}
        self.db['num_users'] += 1
        return user_id

    @SyncOp(self.lock, self)
    def new_photo(self, user_id, file_path):
        '''
            create photo and return id
        '''
        photo_id = self.db['num_photos']
        self.db['photos'][photo_id] = {'sender': user_id, 'file_path': file_path, 'tags': set()}
        self.db['num_photos'] += 1
        return photo_id

    def get_user(self, chat_id):
        '''
            get user id
        '''
        if chat_id not in self.db['chats']:
            logging.warn('there is no such chat registered chat_id:' + str(chat_id))
            return -1

        return self.db['chats'][chat_id]['user']

    def get_vector(self, user_id):
        '''
            get vector id of user by user id
        '''
        if user_id not in self.db['users']:
            logging.warn('There is no such user with user_id:' + str(user_id))
            return -1

        if 'vector' not in self.db['users'][user_id]:
            logging.info('Vector not generated for user yet user_id:' + str(user_id))
            return -1

        return self.db['users'][user_id]['vector']

    def set_avatar(self, user_id, photo_id):
        '''
            set photo as avatar for given user
        '''
        if user_id not in self.db['users']:
            logging.warn('There is no such user with user_id:' + str(user_id))

        if 'avatar' in self.db['users'][user_id]:
            logging.warn('The user has already avatar:' + str(user_id))

        self.db['users'][user_id]['avatar'] = photo_id

    def get_avatar(self, user_id):
        '''
            get photo id of user avatar
        '''
        if user_id not in self.db['users']:
            logging.warn('There is no such user with user_id:' + str(user_id))
            return -1

        return self.db['users'][user_id]['avatar']

    def get_photo_by_vector(self, index):
        '''
            get photo id from vector id
        '''
        pass

    def add_tag_to_photo(self, photo_id, user_id):
        '''
            tag user on given photo
        '''
        pass

    def get_sender(self, photo_id):
        '''
            return user id of photo sender
        '''
        pass

    def get_tags(self, photo_id):
        '''
            get set of user ids tagged in the photo
        '''
        pass

    def get_chat(self, user_id):
        '''
            get chat identifier for given user
        '''
        pass

    def get_photo_path(self, photo_id):
        '''
            get path in filesystem for given photo
        '''
        pass

    def set_vector(self, user_id, vector_id):
        '''
        '''
        pass

    def add_vector(self, photo_id, vector_id):
        '''
            add vector id to list 
        '''
        pass

    def get_user_by_vector(self, vector_id):
        '''
            get user id by vector_id
        '''
        pass