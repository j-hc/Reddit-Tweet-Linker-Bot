from twitter_analyzing import Reasons, Backup, TextPrep, TWSearch
from PyYandexOCR import PyYandexOCR
from rStuff import rPost, rBot
from info import useragent, client_id, client_code, bot_username, bot_pass
from strings import tr, en
from time import sleep
import queue
import threading
import enum
from collections import namedtuple
import traceback
from db import tweet_database

# Some stuff.. ------------------
bad_bot_strs = ["bad bot", "kotu bot", "kötü bot"]
good_bot_strs = ["good bot", "iyi bot", "güzel bot", "cici bot"]
subs_listening_by_new = ["burdurland", "turkey", "svihs", "testyapiyorum", "kgbtr", "gh_ben"]
# subs_listening_by_new = ["testyapiyorum"]
score_listener_interval = 130
sub_feed_listener_interval = 30
notif_listener_interval = 10
# -------------------------------


twJob = namedtuple('twJob', 'to_answer the_post jtype lang')
replyJob = namedtuple('replyJob', 'text thing')


class PriorityEntry:
    def __init__(self, priority, data):
        self.data = data
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority


class JobType(enum.Enum):
    normal = 1
    listing = 2
    goodbot = 3
    badbot = 4


def score_listener():
    try:
        while True:
            scores_id_d = twitterlinker.check_last_comment_scores(limit=30)
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
        while True:
            last_submissions_new = twitterlinker.fetch_posts_from_own_multi(multiname="listening", sort_by="new")
            for last_submission in last_submissions_new:
                if last_submission.is_img:
                    job = twJob(to_answer=last_submission, the_post=last_submission, jtype=JobType.listing,
                                lang=last_submission.lang)
                    job_q.put((2, PriorityEntry(2, job)))
                    print("(SFC)maybe a job: " + last_submission.id_ + " from " + last_submission.subreddit)
                else:
                    print("(SFC)this's not a pic: " + last_submission.id_ + " from " + last_submission.subreddit)
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
            notifs = list(twitterlinker.check_inbox(rkind='t1'))
            if len(notifs) > 0:
                twitterlinker.read_notifs(notifs)
            for notif in notifs:
                job = notif_job_builder(notif)
                if job != -1:
                    print(f"inbox checker: {notif.post_id} from {notif.subreddit}")
                    job_q.put((1, PriorityEntry(1, job)))
            sleep(notif_listener_interval)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def reply_worker(reply_q):
    try:
        while True:
            to_reply = reply_q.get(block=True)[1].data
            answer2 = to_reply.thing
            text = to_reply.text
            print("answer2: " + answer2.id_)
            replied = twitterlinker.send_reply(text=text, thing=answer2)
            if replied != 0:
                reply_q.put((3, PriorityEntry(3, to_reply)))
                sleep(replied)
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def job_handler(job_q, reply_q):
    try:
        while True:
            twjob = job_q.get(block=True)[1].data
            jtype = twjob.jtype
            answer2 = twjob.to_answer
            reply_built = reply_builder(lang=twjob.lang, post=twjob.the_post, jtype=jtype, author=answer2.author)
            if reply_built:
                reply_job = replyJob(text=reply_built, thing=answer2)
                if jtype == JobType.normal:
                    priority = 1
                elif jtype == JobType.listing:
                    priority = 2
                else:
                    priority = 3
                reply_q.put((priority, PriorityEntry(priority, reply_job)))
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


def reply_builder(lang, post, jtype, author):
    try:
        l_res = tr if lang == "tur" else en
        if jtype == JobType.listing:
            messagetxt = "\r\n" + l_res["introduction"] + "\r\n"
            if post.is_gallery:
                imgurl = post.gallery_media[0]
            else:
                imgurl = post.url
            textt = yandex_ocr.get_ocr(imgurl)
            # print(textt)
            if textt:
                prepped_text = TextPrep.prep_text(textt, need_at=True)
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
                        search_twitter = TWSearch.twitter_search(possible_at, possibe_search_text, post.lang)
                        search_twitter_result = search_twitter.get("result")
                        if search_twitter_result == "success":
                            username = search_twitter.get("username")
                            twitlink = search_twitter.get("twitlink")
                            user_id = search_twitter.get("user_id")
                            found_index = search_twitter.get("found_index")
                            print("getting backup archive")
                            backup_link = Backup.capture_tweet_arch(twitlink)

                            tweet_database.insert_data(userid=user_id, twtext=possibe_search_text[found_index],
                                                       backuplink=backup_link)

                            if total_detected_tweets >= 2:
                                messagetxt += l_res["searched_among"].format(total_detected_tweets) + " "
                            messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + l_res[
                                "archive_info"].format(backup_link)
                            messagetxt += l_res["outro"].format(twitterlinker.bot_username)
                            return_none = False
                            break
                        elif search_twitter_result == "error":
                            pass
                            # print("prolly not a tweet: " + post.id_)
                    if return_none:
                        return None
                elif prepped_text_result == "error":
                    # print("prolly not a tweet: " + post.id_)
                    return None
            else:
                # print("prolly not a tweet: " + post.id_)
                return None

        elif jtype == JobType.normal:
            messagetxt = l_res["hello"].format(author) + " " + l_res["introduction"] + "\r\n"
            if post.is_img:
                if post.is_gallery:
                    imgurl = post.gallery_media[0]
                else:
                    imgurl = post.url
                textt = yandex_ocr.get_ocr(imgurl)
                # print(textt)
                if textt:
                    prepped_text = TextPrep.prep_text(textt, need_at=False)
                    prepped_text_result = prepped_text.get("result")
                    if prepped_text_result == "success":
                        searching_for_tweets = prepped_text.get("tweets2search")
                        total_detected_tweets = prepped_text.get("total_detected_tweets")
                        print(f"will search for {len(searching_for_tweets)} tweets")
                        return_err = True
                        for searching_for_tweet in searching_for_tweets:
                            possible_at = searching_for_tweet.possible_at
                            possibe_search_text = searching_for_tweet.possibe_search_text
                            search_twitter = TWSearch.twitter_search(possible_at, possibe_search_text, post.lang)
                            search_twitter_result = search_twitter.get("result")
                            if search_twitter_result == "success":
                                username = search_twitter.get("username")
                                twitlink = search_twitter.get("twitlink")
                                atliatsiz = search_twitter.get("atliatsiz")
                                user_id = search_twitter.get("user_id")
                                found_index = search_twitter.get("found_index")
                                print("getting backup archive")
                                backup_link = Backup.capture_tweet_arch(twitlink)

                                tweet_database.insert_data(userid=user_id, twtext=possibe_search_text[found_index],
                                                           backuplink=backup_link)

                                if total_detected_tweets >= 2:
                                    messagetxt += l_res["searched_among"].format(total_detected_tweets) + " "

                                if atliatsiz:
                                    if searching_for_tweet.no_at_variaton:
                                        messagetxt += l_res["no_at_variation"].format(twitlink)
                                    else:
                                        messagetxt += l_res["couldnt_find_at"].format(username, twitlink)
                                    messagetxt += "\r\n\n" + l_res["archive_info"].format(backup_link)
                                elif not atliatsiz:
                                    messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + \
                                                  l_res["archive_info"].format(backup_link)
                                return_err = False
                                break
                            elif search_twitter_result == "success_db":
                                backup_link = search_twitter.get("db_backup_link")

                                if total_detected_tweets >= 2:
                                    messagetxt += l_res["searched_among"].format(total_detected_tweets) + " "
                                messagetxt += l_res["db_query"].format(backup_link)

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
            messagetxt += l_res["outro"].format(twitterlinker.bot_username)
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
            post = rPost(twitterlinker.get_info_by_id(notif.post_id))
            job = twJob(to_answer=notif, the_post=post, jtype=JobType.normal, lang=post.lang)
            return job
        elif notif.rtype == "comment_reply":
            # BAD BOT
            if any(x in notif.body for x in bad_bot_strs):
                if notif.parent_id in twitterlinker.already_thanked.list:
                    return -1
                else:
                    dt = twitterlinker.get_info_by_id(notif.parent_id)
                    twitterlinker.already_thanked.list.append(notif.parent_id)
                    if any(wrd in dt.get('data').get('body') for wrd in ['kaldırmak', 'to remove', 'tşk', 'tanks']):
                        return -1

                job = twJob(to_answer=notif, the_post=None, jtype=JobType.badbot, lang=notif.lang)
                return job
            # GOOD BOT
            elif any(x in notif.body for x in good_bot_strs):
                if notif.parent_id in twitterlinker.already_thanked.list:
                    return -1
                else:
                    dt = twitterlinker.get_info_by_id(notif.parent_id)
                    twitterlinker.already_thanked.list.append(notif.parent_id)
                    if any(wrd in dt.get('data').get('body') for wrd in ['kaldırmak', 'to remove', 'tşk', 'tanks']):
                        return -1

                job = twJob(to_answer=notif, the_post=None, jtype=JobType.goodbot, lang=notif.lang)
                return job
        else:
            twitterlinker.read_notifs([notif])
        return -1
    except:
        hata = traceback.format_exc()
        with open("hata.txt", "a") as hataf:
            hataf.write(hata + "\n")
        sleep(10)


if __name__ == "__main__":
    # signal.signal(signal.SIGTERM, signal.SIG_IGN)  # FOR HEROKU

    yandex_ocr = PyYandexOCR()
    twitterlinker = rBot(useragent, client_id, client_code, bot_username, bot_pass)
    twitterlinker.create_or_update_multi(multiname="listening", subs=subs_listening_by_new)  # create the multi to listen to

    reply_q = queue.PriorityQueue()
    job_q = queue.PriorityQueue()
    reply_worker_t = threading.Thread(target=reply_worker, args=(reply_q,), daemon=True).start()
    job_handler_t = threading.Thread(target=job_handler, args=(job_q, reply_q), daemon=True).start()
    notif_listener_t = threading.Thread(target=notif_listener, args=(job_q,), daemon=True).start()
    sub_feed_listener_t = threading.Thread(target=sub_feed_listener, args=(job_q,), daemon=True).start()
    score_listener_t = threading.Thread(target=score_listener, daemon=True).start()

    print("everything: OK")
    while True:
        if any(list(job_q.queue)) or any(list(reply_q.queue)):
            print(f"\033[4msearching jobs: {[search[1].data.to_answer for search in list(job_q.queue)]}\033[0m")
            print(f"\033[4mreplying jobs: {[replyy[1].data.thing for replyy in list(reply_q.queue)]}\033[0m")
        sleep(15)
