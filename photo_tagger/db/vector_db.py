import faiss
from ... import settings
from ... import utils
import numpy as np

class FaissEngine:
    '''
        This class implements ACID compliant vector database engine for fast radius search
    '''
    def __init__(self):
        self.index = faiss.IndexFlatL2(settings.descriptor_size)
        print('[INFO] FaissEngine init ...')

    @utils.SingleExec()
    def load(self, db_path):
        self.db_path = db_path
        try:
            self.index = faiss.read_index(db_path)
            print('[INFO] faiss load success at path:', db_path)
        except:
            print('[ERROR] Unable to load faiss index at path: ', db_path)

    @utils.SingleExec()
    def dump(self, db_path=None):
        try:
            if db_path is None:
                faiss.write_index(self.index, self.db_path)
            else:
                faiss.write_index(self.index, db_path)
            print('[INFO] faiss dump success at path:', db_path)
        except:
            print('[WARNING] faiss dump failed at path:', db_path)

    @utils.SingleExec()
    def add(self, vector):
        try:
            self.index.add(vector.reshape((1, -1)))
            return self.index.ntotal - 1
        except Exception as e:
            print('[EXCEPTION] ', e)
            print('[ERROR] vector is not added to faiss index')

    @utils.SingleExec()
    def remove(self, vector_id):
        if vector_id < 0 or vector_id >= index.ntotal:
            print('[ERROR] incorrect vector_id for faiss index removal')
            return False
        else:
            self.index.remove_ids(np.asarray([vector_id]))
            return True