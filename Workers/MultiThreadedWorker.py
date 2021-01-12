from threading import Thread
import queue
from .Utils import JobHandlerWorker
from .RedditWorkers import RedditWorkers
# from PyYandexOCR import PyYandexOCR
from VisionOCR import VisionOCR
from TwitterClient import TwitterClient


class MultiThreadedWorker:
    def __init__(self, rbot):
        self.reply_q = queue.PriorityQueue()
        self.job_q = queue.PriorityQueue()

        reddit_workers = RedditWorkers(rbot, self.job_q, self.reply_q)

        # yandex_ocr = PyYandexOCR()
        vision_ocr = VisionOCR
        tw_client = TwitterClient()
        job_handler_worker = JobHandlerWorker(vision_ocr, tw_client, self.job_q, self.reply_q)

        self.reply_worker_t = Thread(target=reddit_workers.reply_worker, daemon=True)
        self.notif_listener_t = Thread(target=reddit_workers.notif_listener, daemon=True)
        self.sub_feed_listener_t = Thread(target=reddit_workers.sub_feed_listener, daemon=True)
        self.score_listener_t = Thread(target=reddit_workers.score_listener, daemon=True)

        self.job_handler_t = Thread(target=job_handler_worker.job_handler, daemon=True)

    def run_threads(self):
        self.reply_worker_t.start()
        self.job_handler_t.start()
        self.notif_listener_t.start()
        self.sub_feed_listener_t.start()
        self.score_listener_t.start()
