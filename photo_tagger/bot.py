from workers import Distributor
from workers import TelegramBot
import settings

if __name__ == '__main__':
    distributor = Distributor('data/meta.db', 'data/faces.faiss', 'data/photos.faiss')
    frontend = TelegramBot(distributor, "data/photos/")
    frontend.start()