from api_and_twitterparsing import Reasons, capture_tweet_arch, vision_ocr, prep_text, twitter_search
from rBot import rBot
from info import useragent, client_id, client_code, bot_username, bot_pass
from strings import tr, en
from time import sleep
import queue
import threading
from rUtils import rUtils
import enum
from collections import namedtuple
import traceback

# Some stuff.. ------------------
bad_bot_strs = ["bad bot", "kotu bot", "kötü bot"]
good_bot_strs = ["good bot", "iyi bot", "güzel bot", "cici bot"]
subs_listening = ["turkey", "svihs"]
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
    try:
        while True:
            scores_id_d = twitterlinker.check_last_comment_scores(limit=7)
            for score_id in scores_id_d:
                if scores_id_d[score_id] <= -3:
                    twitterlinker.del_comment(score_id)
            sleep(score_listener_interval)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def sub_feed_listener(job_q):
    try:
        # SUBREDDIT FEED CHECK
        checked_posts = []
        while True:
            if len(checked_posts) > 50:
                checked_posts = []
            last_submissions = rUtils.fetch_subreddit_posts(subs_listening, limit=3)
            for last_submission in last_submissions:
                if not rUtils.check_if_already_post(last_submission, checked_posts, twitterlinker.bot_username):
                    if rUtils.is_img_post(last_submission):
                        job = twJob(to_answer=last_submission, the_post=last_submission, jtype=JobType.listing,
                                    lang=last_submission.lang)
                        job_q.put(job)
                        print("(SFC)maybe a job: " + last_submission.id_ + " from " + last_submission.subreddit)
                    else:
                        print("(SFC)this's not a pic: " + last_submission.id_ + " from " + last_submission.subreddit)
                #else:
                    #print("(SFC)already: " + last_submission.id_, end=' |')
            sleep(sub_feed_listener_interval)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def notif_listener(job_q):
    try:
        # INBOX CHECK
        while True:
            notifs = twitterlinker.check_inbox(rkind='t1')
            notifs = list(notifs)
            if len(notifs) > 0:
                twitterlinker.read_notifs(notifs)
                for notif in notifs:
                    job = notif_job_builder(notif)
                    if job != -1:
                        print(f"inbox checker: {notif.post_id} from {notif.subreddit}")
                        job_q.put(job)
            sleep(notif_listener_interval)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def reply_worker(reply_q):
    try:
        while True:
            to_reply = reply_q.get(block=True)
            answer2 = to_reply.thing
            text = to_reply.text
            print("answer2: " + answer2.id_)
            replied = twitterlinker.send_reply(text=text, thing=answer2)
            if replied != 0:
                reply_q.put(to_reply)
                sleep(replied)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def job_handler(job_q, reply_q):
    try:
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
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def reply_builder(lang, post, jtype, author):
    try:
        l_res = tr if lang == "tur" else en
        if jtype == JobType.listing and rUtils.is_img_post(post):
            messagetxt = "\r\n" + l_res["introduction"] + "\r\n"
            textt = vision_ocr(post.url)
            if textt:
                prepped_text = prep_text(textt, need_at=True)
                prepped_text_result = prepped_text.get("result")
                if prepped_text_result == "success":
                    searching_for_tweets = prepped_text.get("tweets2search")
                    total_detected_tweets = prepped_text.get("total_detected_tweets")
                    print(f"will search for {len(searching_for_tweets)} tweets")
                    print(searching_for_tweets)
                    return_none = True
                    for searching_for_tweet in searching_for_tweets:
                        possible_at = searching_for_tweet.possible_at
                        possibe_search_text = searching_for_tweet.possibe_search_text
                        search_twitter = twitter_search(possible_at, possibe_search_text, post.lang)
                        search_twitter_result = search_twitter.get("result")
                        if search_twitter_result == "success":
                            username = search_twitter.get("username")
                            twitlink = search_twitter.get("twitlink")
                            print("getting backup archive")
                            backup_link = capture_tweet_arch(twitlink)
                            if len(searching_for_tweets) > 1:
                                messagetxt += l_res["searched_among"].format(total_detected_tweets) + " "
                            messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + l_res["archive_info"].format(backup_link)
                            messagetxt += l_res["outro"]
                            return_none = False
                            break
                        elif search_twitter_result == "error":
                            print("prolly not a tweet: " + post.id_)
                    if return_none:
                        return None
                elif prepped_text_result == "error":
                    print("prolly not a tweet: " + post.id_)
                    return None
            else:
                print("prolly not a tweet: " + post.id_)
                return None

        elif jtype == JobType.normal:
            messagetxt = l_res["hello"].format(author) + " " + l_res["introduction"] + "\r\n"
            if rUtils.is_img_post(post):
                textt = vision_ocr(post.url)
                if textt:
                    prepped_text = prep_text(textt, need_at=False)
                    prepped_text_result = prepped_text.get("result")
                    if prepped_text_result == "success":
                        searching_for_tweets = prepped_text.get("tweets2search")
                        total_detected_tweets = prepped_text.get("total_detected_tweets")
                        print(f"will search for {len(searching_for_tweets)} tweets")
                        return_err = True
                        for searching_for_tweet in searching_for_tweets:
                            possible_at = searching_for_tweet.possible_at
                            possibe_search_text = searching_for_tweet.possibe_search_text
                            search_twitter = twitter_search(possible_at, possibe_search_text, post.lang)
                            search_twitter_result = search_twitter.get("result")
                            if search_twitter_result == "success":
                                username = search_twitter.get("username")
                                twitlink = search_twitter.get("twitlink")
                                atliatsiz = search_twitter.get("atliatsiz")
                                print("getting backup archive")
                                backup_link = capture_tweet_arch(twitlink)
                                if len(searching_for_tweets) > 1:
                                    messagetxt += l_res["searched_among"].format(total_detected_tweets) + " "
                                if atliatsiz:
                                    messagetxt += l_res["couldnt_find_at"].format(username, twitlink)+ "\r\n\n" + \
                                                  l_res["archive_info"].format(backup_link)
                                elif not atliatsiz:
                                    messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + \
                                                  l_res["archive_info"].format(backup_link)
                                return_err = False
                                break
                            elif search_twitter_result == "error":
                                reason_enum = search_twitter.get("reason")
                                return_err = True

                        if return_err:
                            if reason_enum == Reasons.DEFAULT:
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
                        elif reason_enum == Reasons.TOO_SHORT_NO_AT:
                            reason_txt = l_res["reason_tooshort"]
                        elif reason_enum == Reasons.ACCOUNT_SUSPENDED:
                            acc = prepped_text.get("suspended_account")
                            reason_txt = l_res["reason_accountsuspended"].format(acc)
                        elif reason_enum == Reasons.ACCOUNT_DNE:
                            acc = prepped_text.get("dne_account")
                            reason_txt = l_res["reason_accountdne"].format(acc)
                        elif reason_enum == Reasons.ACCOUNT_PROTECTED:
                            acc = prepped_text.get("protected_account")
                            reason_txt = l_res["reason_accountprotected"].format(acc)
                        else:
                            reason_txt = l_res["reason_default"]
                        messagetxt += l_res["because"].format(reason_txt)

                else:  # NO TEXT
                    reason_txt = l_res["reason_notext"]
                    messagetxt += l_res["because"].format(reason_txt)
            else:  # NOT IMG POST
                print('called onto a text post')
                reason_txt = "\r\n" + l_res["reason_no_image"]
                messagetxt += l_res["because"].format(reason_txt)
            messagetxt += l_res["outro"]
        elif jtype == JobType.badbot:
            print("bad bot")
            messagetxt = l_res["badbot"]
        elif jtype == JobType.goodbot:
            print("good bot")
            messagetxt = l_res["goodbot"]
        return messagetxt
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def notif_job_builder(notif):
    try:
        if notif.rtype == 'username_mention':
            post = rUtils.fetch_post_from_notif(notif)
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
        else:
            return -1
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


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
        if any(list(job_q.queue)) or any(list(reply_q.queue)):
            print(f"\033[4msearching jobs: {[search.to_answer for search in list(job_q.queue)]}\033[0m")
            print(f"\033[4mreplying jobs: {[replyy.thing for replyy in list(reply_q.queue)]}\033[0m")
        sleep(30)

