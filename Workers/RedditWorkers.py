from time import sleep
import traceback
from collections import namedtuple
from .Utils import JobType, PriorityEntry
from rStuff import PostFetcher


class RedditWorkers:
    bad_bot_strs = ["bad bot", "kotu bot", "kötü bot"]
    good_bot_strs = ["good bot", "iyi bot", "güzel bot", "cici bot"]

    twitterJob = namedtuple('twitterJob', 'to_answer the_post jtype lang')

    def __init__(self, rbot, job_q, reply_q):
        self.rbot = rbot

        self.reply_q = reply_q
        self.job_q = job_q

        self.score_listener_interval = 130
        self.sub_feed_listener_interval = 28
        self.notif_listener_interval = 9

    def score_listener(self):
        try:
            while True:
                scores_id_d = self.rbot.check_last_comment_scores(limit=30)
                for score_id in scores_id_d:
                    if scores_id_d[score_id] <= -3:
                        self.rbot.del_comment(score_id)
                sleep(self.score_listener_interval)
        except:
            while True:
                traceback.print_exc()
                sleep(2)

    def sub_feed_listener(self):
        try:
            posts_fetcher = PostFetcher(bot=self.rbot, multiname="listening", sort_by="new")
            while True:
                last_submissions_new = posts_fetcher.fetch_posts()
                for last_submission in last_submissions_new:
                    if last_submission.is_img:
                        job = self.twitterJob(to_answer=last_submission, the_post=last_submission, jtype=JobType.listing,
                                              lang=last_submission.lang)
                        self.job_q.put((2, PriorityEntry(2, job)))
                        print("(SFC)maybe a job: " + last_submission.id_ + " from " + last_submission.subreddit)
                    # else:
                        # print("(SFC)this's not a pic: " + last_submission.id_ + " from " + last_submission.subreddit)
                sleep(self.sub_feed_listener_interval)
        except:
            while True:
                traceback.print_exc()
                sleep(2)

    def notif_listener(self):
        try:
            # INBOX CHECK
            while True:
                notifs = list(self.rbot.check_inbox(rkind='t1'))
                if len(notifs) > 0:
                    self.rbot.read_notifs(notifs)
                for notif in notifs:
                    job = self._notif_job_builder(notif)
                    if job != -1:
                        print(f"inbox checker: {notif.post_id} from {notif.subreddit}")
                        self.job_q.put((1, PriorityEntry(1, job)))
                sleep(self.notif_listener_interval)
        except:
            while True:
                traceback.print_exc()
                sleep(2)

    def reply_worker(self):
        try:
            while True:
                to_reply = self.reply_q.get(block=True)[1].data
                answer2 = to_reply.thing
                text = to_reply.text
                replied = self.rbot.send_reply(text=text, thing=answer2)
                if replied != 0:
                    self.reply_q.put((3, PriorityEntry(3, to_reply)))
                    sleep(replied)
        except:
            while True:
                traceback.print_exc()
                sleep(2)

    def _notif_job_builder(self, notif):
        if notif.rtype == 'username_mention':
            post = self.rbot.get_info_by_id(notif.post_id)
            job = self.twitterJob(to_answer=notif, the_post=post, jtype=JobType.normal, lang=post.lang)
            return job
        elif notif.rtype == "comment_reply":
            # BAD BOT
            if any(x in notif.body.lower() for x in self.bad_bot_strs):
                if notif.parent_id in self.rbot.already_thanked.list:
                    return -1
                else:
                    dt = self.rbot.get_info_by_id(notif.parent_id)
                    self.rbot.already_thanked.append_elem(notif.parent_id)
                    if any(wrd in dt['data']['children'][0]["data"]["body"].lower() for wrd in [':(', 'to remove', 'tşk', 'tanks']):
                        return -1
                job = self.twitterJob(to_answer=notif, the_post=None, jtype=JobType.badbot, lang=notif.lang)
                return job
            # GOOD BOT
            elif any(x in notif.body.lower() for x in self.good_bot_strs):
                if notif.parent_id in self.rbot.already_thanked.list:
                    return -1
                else:
                    dt = self.rbot.get_info_by_id(notif.parent_id)
                    self.rbot.already_thanked.append_elem(notif.parent_id)
                    if any(wrd in dt['data']['children'][0]["data"]["body"].lower() for wrd in [':(', 'to remove', 'tşk', 'tanks']):
                        return -1

                job = self.twitterJob(to_answer=notif, the_post=None, jtype=JobType.goodbot, lang=notif.lang)
                return job
        else:
            self.rbot.read_notifs([notif])
        return -1
