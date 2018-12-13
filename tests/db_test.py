import json
import sys
sys.path.append('../photo_tagger/db/')
from meta_db import DumbDB

def viz_dict(data):
	print(json.dumps(x, indent=2))

import unittest

class TestDB(unittest.TestCase):

    def test_load_dump(self):
    	db = DumbDB('temp.db')
    	db.load()
    	db.dump()

        

if __name__ == '__main__':
    unittest.main()