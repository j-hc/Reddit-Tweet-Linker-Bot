from Workers import MultiThreadedWorker
from rStuff import rBot
from info import *
from time import sleep

if __name__ == '__main__':
    twitterlinker = rBot(useragent, client_id, client_code, bot_username, bot_pass)

    subs_listening_by_new = ["turkey", "svihs", "testyapiyorum", "kgbtr", "ateistturk"]
    twitterlinker.create_or_update_multi(multiname="listening", subs=subs_listening_by_new)  # create the multi to listen to

    multi_threaded_worker = MultiThreadedWorker(twitterlinker)
    multi_threaded_worker.run_threads()

    while True:
        if any(list(multi_threaded_worker.job_q.queue)) or any(list(multi_threaded_worker.reply_q.queue)):
            print(f"searching jobs: {[search[1].data.to_answer for search in list(multi_threaded_worker.job_q.queue)[:10]]}")
            print(f"replying jobs: {[replyy[1].data.thing for replyy in list(multi_threaded_worker.reply_q.queue)[:10]]}")
        sleep(15)
