import json
import sys
sys.path.append('../photo_tagger/db/')
from meta_db import DumbDB

def viz_dict(data):
	print(json.dumps(data, indent=2))


        

if __name__ == '__main__':
    db = DumbDB('temp.db')
    db.new_user(0, "admin")
    print('wtf')
    viz_dict(db.db)
