import pickle
import threading
import logging
import contextlib

class SyncOp(contextlib.ContextDecorator):
    def __init__(self, lock, db):
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

def sync(fn):
    def wrapped(outer_self, *args, **kwargs):
        outer_self.lock.acquire()
        outer_self.db.load()
        result = fn(outer_self, *args, **kwargs)
        outer_self.db.dump()
        outer_self.lock.release()
        return result
    return wrapped
 

class DumbDB:
    '''
        Dumbest DB engine ever
    '''
    def __init__(self, load_path):
        self.db = {'chats': {}, 'users': {}, 'photos': {}, 'photo_vectors': {}, 'user_vectors': {}, 'num_users': 0, 'num_photos': 0}
        self.lock = threading.Lock()
        self.load_path = load_path
    
    def load(self, load_path = None):
        if load_path is not None:
            self.load_path = load_path

        try:
            with open(self.load_path, 'rb') as file:
                self.db = pickle.load(file)
        except:
            logging.error("Couldn't load meta db, starting from scratch")

    def dump(self):
        with open(self.load_path, 'wb') as file:
            pickle.dump(self.db, file)

    @sync
    def new_user(self, chat_id, username):
        '''
            create user and return unique id
        '''
        user_id = self.db['num_users']
        self.db['chats'][chat_id] = {'user': user_id}
        self.db['users'][user_id] = {'chat': chat_id, 'avatar': None, 'username': username}
        self.db['num_users'] += 1
        return user_id

    @sync
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

    @sync
    def set_avatar(self, user_id, photo_id):
        '''
            set photo as avatar for given user
        '''
        if user_id not in self.db['users']:
            logging.warn('There is no such user with user_id:' + str(user_id))
            return

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
        if index not in self.db['photo_vectors']:
            logging.error('There is no photo associated with vector: ' + str(index))
            return -1

        return self.db['photo_vectors'][index]

    @sync
    def add_tag_to_photo(self, photo_id, user_id):
        '''
            tag user on given photo
        '''
        if photo_id not in self.db['photos']:
            logging.warn('There is no such photo with photo_id:' + str(photo_id))
            return -1

        self.db['photos'][photo_id]['tags'].add(user_id)

    @sync
    def get_sender(self, photo_id):
        '''
            return user id of photo sender
        '''
        if photo_id not in self.db['photos']:
            logging.warn('There is no such photo with photo_id:' + str(photo_id))
            return -1
        
        return self.db['photos'][photo_id]['sender']

    @sync
    def get_tags(self, photo_id):
        '''
            get set of user ids tagged in the photo
        '''
        if photo_id not in self.db['photos']:
            logging.warn('There is no such photo with photo_id:' + str(photo_id))
            return set(-1)

        return self.db['photos'][photo_id]['tags']

    def get_chat(self, user_id):
        '''
            get chat identifier for given user
        '''
        if user_id not in self.db['users']:
            logging.warn('There is no such user with user_id:' + str(user_id))
            return -1

        return self.db['users'][user_id]['chat']

    def get_photo_path(self, photo_id):
        '''
            get path in filesystem for given photo
        '''
        if photo_id not in self.db['photos']:
            logging.warn('There is no such photo with photo_id:' + str(photo_id))
            return -1

        return self.db['photos'][photo_id]['file_path']

    @sync
    def set_vector(self, user_id, vector_id):
        '''
            set descriptor vector id for given user
        '''
        if user_id not in self.db['users']:
            logging.error('There is no such user with user_id:' + str(user_id))
            return

        self.db['users'][user_id]['vector'] = vector_id
        self.db['user_vectors'][vector_id] = user_id

    @sync
    def add_vector(self, photo_id, vector_id):
        '''
            add vector id to list 
        '''
        if photo_id not in self.db['photos']:
            logging.error('There is no such photo with photo_id:' + str(photo_id))
            return
        
        self.db['photo_vectors'][vector_id] = photo_id

    def get_user_by_vector(self, vector_id):
        '''
            get user id by vector_id
        '''
        if user_id not in self.db['users']:
            logging.error('There is no such user with user_id:' + str(user_id))
            return -1

        return self.db['user_vectors'][vector_id]

    def get_username(self, user_id):
        return self.db['users'][user_id]['username']
