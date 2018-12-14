from workers import Distributor
from workers import TelegramBot
import settings
import logging


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.INFO)

if __name__ == '__main__':
    distributor = Distributor('data/meta.db', 'data/faces.faiss', 'data/photos.faiss')
    frontend = TelegramBot(distributor, "data/photos/")
    frontend.manual_add(178150010, '/home/zhan/photos/*')
    frontend.start()
