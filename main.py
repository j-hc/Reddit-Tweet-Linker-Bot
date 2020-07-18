from api_and_twitterparsing import *
from rBot import rBot
from info import useragent, client_id, client_code, bot_username, bot_pass
from strings import tr, en
from time import sleep
import queue
import threading
from rUtils import check_if_already_post, is_img_post, fetch_post_from_notif, fetch_subreddit_posts
import enum
from collections import namedtuple

# Some stuff.. ------------------
bad_bot_strs = ["bad bot", "kotu bot", "kötü bot"]
good_bot_strs = ["good bot", "iyi bot", "güzel bot", "cici bot"]
subs_listening = ["svihs", "turkey", "kgbtr"]
score_listener_interval = 130
sub_feed_listener_interval = 30
notif_listener_interval = 10
# -------------------------------


class JobType(enum.Enum):
    normal = 1
    listing = 2
    goodbot = 3
    badbot = 4


twJob = namedtuple('twJob', 'to_answer the_post jtype lang')
replyJob = namedtuple('replyJob', 'text thing')


def score_listener():
    while True:
        scores = twitterlinker.check_last_comment_scores(limit=5)
        for score_j in scores:
            score = score_j["data"]["score"]
            if score <= -2:
                twitterlinker.del_comment(score_j["data"]["name"])
        sleep(score_listener_interval)


def sub_feed_listener(job_q):
    # SUBREDDIT FEED CHECK
    checked_posts = []
    while True:
        if len(checked_posts) > 50:
            checked_posts = []
        last_submissions = fetch_subreddit_posts(subs_listening, limit=2)
        for last_submission in last_submissions:
            if not check_if_already_post(last_submission, checked_posts, twitterlinker.bot_username):
                if is_img_post(last_submission):
                    job = twJob(to_answer=last_submission, the_post=last_submission, jtype=JobType.listing,
                                lang=last_submission.lang)
                    job_q.put(job)
                    print("(SFC)maybe a job: " + last_submission.id_ + " from " + last_submission.subreddit)
                else:
                    print("(SFC)this's not a pic: " + last_submission.id_ + " from " + last_submission.subreddit)
            else:
                print("(SFC)already: " + last_submission.id_, end=' |')
        print()
        sleep(sub_feed_listener_interval)


def notif_listener(job_q):
    # INBOX CHECK
    while True:
        notifs = twitterlinker.check_inbox()
        notifs = list(notifs)
        if len(notifs) > 0:
            twitterlinker.read_notifs(notifs)
            for notif in notifs:
                job = notif_job_builder(notif)
                if job != -1:
                    print(f"inbox checker: {notif.post_id} from {notif.subreddit}")
                    job_q.put(job)
        sleep(notif_listener_interval)


def reply_worker(reply_q):
    while True:
        to_reply = reply_q.get(block=True)
        answer2 = to_reply.thing
        text = to_reply.text
        print("answer2: " + answer2.id_)
        replied = twitterlinker.send_reply(text=text, thing=answer2)
        if replied != 0:
            reply_q.put(to_reply)
            sleep(replied)


def job_handler(job_q, reply_q):
    while True:
        twjob = job_q.get(block=True)
        jtype = twjob.jtype
        post = twjob.the_post
        lang = twjob.lang
        answer2 = twjob.to_answer

        reply_built = reply_builder(lang=lang, post=post, jtype=jtype, author=answer2.author)
        if reply_built:
            reply_job = replyJob(text=reply_built, thing=answer2)
            reply_q.put(reply_job)
            if post:
                print('search DONE: ', post.id_)
            else:
                print('search DONE: ', answer2.id_)


def reply_builder(lang, post, jtype, author):
    l_res = tr if lang == "tur" else en
    if jtype == JobType.listing and is_img_post(post):
        messagetxt = "\r\n" + l_res["introduction"] + "\r\n"
        textt = vision_ocr(post.url)
        if textt:
            prepped_text = prep_text(textt, need_at=True)
            prepped_text_result = prepped_text.get("result")
            if prepped_text_result == "success":
                possible_at = prepped_text.get("possible_at")
                possibe_search_text = prepped_text.get("possibe_search_text")
                search_twitter = twitter_search(possible_at, possibe_search_text, post.lang)
                search_twitter_result = search_twitter.get("result")
                if search_twitter_result == "success":
                    username = search_twitter.get("username")
                    twitlink = search_twitter.get("twitlink")
                    print("getting backup archive")
                    backup_link = capture_tweet_arch(twitlink)
                    messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + l_res["archive_info"].format(backup_link)
                    messagetxt += l_res["outro"]
                elif search_twitter_result == "error":
                    print("prolly not a tweet: " + post.id_)
                    return None
            elif prepped_text_result == "error":
                print("prolly not a tweet: " + post.id_)
                return None
        else:
            print("prolly not a tweet: " + post.id_)
            return None

    elif jtype == JobType.normal:
        messagetxt = l_res["hello"].format(author) + " " + l_res["introduction"] + "\r\n"
        if is_img_post(post):
            textt = vision_ocr(post.url)
            if textt:
                prepped_text = prep_text(textt, need_at=False)
                prepped_text_result = prepped_text.get("result")
                if prepped_text_result == "success":
                    possible_at = prepped_text.get("possible_at")
                    possibe_search_text = prepped_text.get("possibe_search_text")
                    search_twitter = twitter_search(possible_at, possibe_search_text, post.lang)
                    search_twitter_result = search_twitter.get("result")
                    if search_twitter_result == "success":
                        username = search_twitter.get("username")
                        twitlink = search_twitter.get("twitlink")
                        atliatsiz = search_twitter.get("atliatsiz")

                        print("getting backup archive")
                        backup_link = capture_tweet_arch(twitlink)

                        if atliatsiz:
                            messagetxt += l_res["couldnt_find_at"].format(username, twitlink)
                        elif not atliatsiz:
                            messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + \
                                          l_res["archive_info"].format(backup_link)

                    elif search_twitter_result == "error":
                        reason_enum = search_twitter.get("reason")
                        if reason_enum == Reasons.NO_TEXT:
                            reason_txt = l_res["reason_default"]
                        else:
                            reason_txt = l_res["reason_default"]
                        messagetxt += l_res["because"].format(reason_txt)

                elif prepped_text_result == "error":
                    reason_enum = prepped_text.get("reason")
                    if reason_enum == Reasons.NO_TEXT:
                        reason_txt = l_res["reason_notext"]
                    elif reason_enum == Reasons.NO_AT:
                        reason_txt = l_res["reason_notext"]
                    elif reason_enum == Reasons.ACCOUNT_SUSPENDED:
                        reason_txt = l_res["reason_accountsuspended"]
                    else:
                        reason_txt = l_res["reason_default"]
                    messagetxt += l_res["because"].format(reason_txt)

            else:  # NO TEXT
                reason_txt = l_res["reason_notext"]
                messagetxt += l_res["because"].format(reason_txt)
        else:  # NOT IMG POST
            print('called onto a text post')
            reason_txt = "\r\n" + l_res["no_image_err"]
            messagetxt += l_res["because"].format(reason_txt)
        messagetxt += l_res["outro"]
    elif jtype == JobType.badbot:
        print("bad bot")
        messagetxt = l_res["badbot"]
    elif jtype == JobType.goodbot:
        print("good bot")
        messagetxt = l_res["goodbot"]
    return messagetxt


def notif_job_builder(notif):
    if notif.kind == "t4":
        return -1
    elif notif.rtype == 'username_mention':
        post = fetch_post_from_notif(notif)
        job = twJob(to_answer=notif, the_post=post, jtype=JobType.normal, lang=post.lang)
        return job
    elif notif.rtype == "comment_reply":
        # BAD BOT
        if any(x in notif.body for x in bad_bot_strs):
            job = twJob(to_answer=notif, the_post=None, jtype=JobType.badbot, lang=notif.lang)
            return job
        # GOOD BOT
        elif any(x in notif.body for x in good_bot_strs):
            job = twJob(to_answer=notif, the_post=None, jtype=JobType.goodbot, lang=notif.lang)
            return job
    return -1


if __name__ == "__main__":
    twitterlinker = rBot(useragent, client_id, client_code, bot_username, bot_pass)

    reply_q = queue.Queue()
    job_q = queue.Queue()
    reply_worker_t = threading.Thread(target=reply_worker, args=(reply_q,), daemon=True)
    job_handler_t = threading.Thread(target=job_handler, args=(job_q, reply_q), daemon=True)
    notif_listener_t = threading.Thread(target=notif_listener, args=(job_q,), daemon=True)
    sub_feed_listener_t = threading.Thread(target=sub_feed_listener, args=(job_q,), daemon=True)
    score_listener_t = threading.Thread(target=score_listener, daemon=True)

    reply_worker_t.start()
    job_handler_t.start()
    notif_listener_t.start()
    sub_feed_listener_t.start()
    score_listener_t.start()

    while True:
        print(f"\033[4msearching jobs: {[search.to_answer for search in list(job_q.queue)]}\033[0m")
        print(f"\033[4mreplying jobs: {[replyy.to_answer for replyy in list(reply_q.queue)]}\033[0m")
        sleep(17)
