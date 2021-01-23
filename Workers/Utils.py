import enum
from strings import tr, en
from twitter_analyzing import Backup, Reasons, TextPrep, TWSearch
from collections import namedtuple
import traceback
from time import sleep


class JobType(enum.Enum):
    normal = 1
    listing = 2
    goodbot = 3
    badbot = 4


class PriorityEntry:
    def __init__(self, priority, data):
        self.data = data
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority


class JobHandlerWorker:
    replyJob = namedtuple('replyJob', 'text thing')

    def __init__(self, ocr_tool, tw_client, job_q, reply_q):
        self.ocr_tool = ocr_tool

        self.text_prepper = TextPrep(tw_client)
        self.twitter_searcher = TWSearch(tw_client)

        self.job_q = job_q
        self.reply_q = reply_q

    def job_handler(self):
        try:
            while True:
                twjob = self.job_q.get(block=True)[1].data
                jtype = twjob.jtype
                answer2 = twjob.to_answer
                reply_built = self._reply_builder(lang=twjob.lang, post=twjob.the_post, jtype=jtype, author=answer2.author)
                if reply_built:
                    reply_job = self.replyJob(text=reply_built, thing=answer2)
                    if jtype == JobType.normal:
                        priority = 1
                    elif jtype == JobType.listing:
                        priority = 2
                    else:
                        priority = 3
                    self.reply_q.put((priority, PriorityEntry(priority, reply_job)))
        except:
            while True:
                traceback.print_exc()
                sleep(2)

    def _reply_builder(self, lang, post, jtype, author):
        l_res = tr if lang == "tur" else en
        if jtype == JobType.listing:
            messagetxt = "\r\n" + l_res["introduction"] + "\r\n"
            if post.is_gallery:
                imgurl = post.gallery_media[0]
            else:
                imgurl = post.url
            textt = self.ocr_tool.get_ocr(imgurl)
            if textt:
                prepped_text = self.text_prepper.prep_text(textt, need_at=True)
                prepped_text_result = prepped_text.get("result")
                if prepped_text_result == "success":
                    searching_for_tweets = prepped_text.get("tweets2search")
                    print(f"will search for {len(searching_for_tweets)} tweets")
                    print(searching_for_tweets)

                    search_twitter = self.twitter_searcher.twitter_search(searching_for_tweets, post.lang)
                    search_twitter_result = search_twitter.get("result")
                    if search_twitter_result == "success":
                        username = search_twitter.get("username")
                        twitlink = search_twitter.get("twitlink")
                        # user_id = search_twitter.get("user_id")
                        # found_index = search_twitter.get("found_index")
                        print("getting backup archive")
                        backup_link = Backup.capture_tweet_arch(twitlink)
                        # tweet_database.insert_data(userid=user_id, twtext=possibe_search_text[found_index],
                        #                            backuplink=backup_link)
                        messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + l_res["archive_info"].format(backup_link)
                        messagetxt += l_res["outro"]
                    elif search_twitter_result == "error":
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
                textt = self.ocr_tool.get_ocr(imgurl)
                # print(textt)
                if textt:
                    prepped_text = self.text_prepper.prep_text(textt, need_at=False)
                    prepped_text_result = prepped_text.get("result")
                    if prepped_text_result == "success":
                        searching_for_tweets = prepped_text.get("tweets2search")
                        print(f"will search for {len(searching_for_tweets)} tweets")

                        search_twitter = self.twitter_searcher.twitter_search(searching_for_tweets, post.lang)
                        search_twitter_result = search_twitter.get("result")
                        if search_twitter_result == "success":
                            username = search_twitter.get("username")
                            twitlink = search_twitter.get("twitlink")
                            atliatsiz = search_twitter.get("atliatsiz")
                            no_at_variaton = search_twitter.get("no_at_variaton")
                            # user_id = search_twitter.get("user_id")
                            # found_index = search_twitter.get("found_index")
                            print("getting backup archive")
                            backup_link = Backup.capture_tweet_arch(twitlink)

                            # tweet_database.insert_data(userid=user_id, twtext=possibe_search_text[found_index],
                            #                            backuplink=backup_link)

                            if atliatsiz:
                                if no_at_variaton:
                                    messagetxt += l_res["no_at_variation"].format(twitlink)
                                else:
                                    messagetxt += l_res["couldnt_find_at"].format(username, twitlink)
                                messagetxt += "\r\n\n" + l_res["archive_info"].format(backup_link)
                            elif not atliatsiz:
                                messagetxt += l_res["success"].format(username, twitlink) + "\r\n\n" + \
                                              l_res["archive_info"].format(backup_link)
                        elif search_twitter_result == "success_db":
                            backup_link = search_twitter.get("db_backup_link")
                            messagetxt += l_res["db_query"].format(backup_link)
                        elif search_twitter_result == "error":
                            reason_enum = search_twitter.get("reason")
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