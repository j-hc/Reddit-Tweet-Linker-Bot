from .err_reasons import Reasons
from .TW_user_status import TWStatus
import re
from math import ceil
from collections import namedtuple
from .twitter_client import tw_client


class TextPrep:
    replying_to = ["antwort an", "replying to", " adlı kişiye", " adlı kullanıcılara", "svar till"]
    endhere = ['Twitter for', 'Translate Tweet', 'Twitter Web App', 'PM - ', '20 - ', '19 - ', 'for iOS', 'for Android',
               ' · ', ' Translate from ', 'Tweet your reply', 'Show this thread', 'Yanıtını Tweetle', ' - 1', ' - 2',
               ' - 3', 'dilinden Google tarafından']
    tweet_search_model = namedtuple("tweet_search_model", "possible_at possibe_search_text no_at_variaton")

    @staticmethod
    def prep_text(text, need_at):
        split_loaded = text.strip().split('\n')

        start_index = len(split_loaded) - 1
        tweet_search_models = []
        last_err = None
        total_detected_tweets = 0
        while not start_index == -1:
            at = None
            below_this = None
            for at_dnm in range(start_index, -1, -1):
                at_dnm_txt = str(split_loaded[at_dnm])
                at_dnm_txt_low = at_dnm_txt.lower()
                if "@" in at_dnm_txt:
                    if any(yasak in at_dnm_txt_low for yasak in TextPrep.replying_to):
                        below_this = at_dnm + 1
                    else:
                        extrct_at = at_dnm_txt.split('@')[1].split()
                        if bool(extrct_at):
                            if len(extrct_at) >= 1:
                                if len(' '.join(extrct_at[1:])) < 7 or ' · ' in at_dnm_txt:
                                    at = extrct_at[0]
                                    break
                                else:
                                    continue
                            else:
                                at = extrct_at[0]
                                break

            if at is None:
                #print("@username gozukmuyor")
                possible_at = None
                if need_at:  # which means, called from a listing job
                    last_err = {"result": "error", "reason": Reasons.NO_AT}
                    start_index = at_dnm - 1
                    continue
            else:
                find_at = at
                if not bool(re.fullmatch(r"[A-Za-z0-9_]{4,15}", find_at)):
                    if not below_this:
                        below_this = at_dnm + 1
                    possible_at = None
                    if need_at:  # which means, called from a listing job
                        last_err = {"result": "error", "reason": Reasons.NO_AT}
                        start_index = at_dnm - 1
                        continue
                else:
                    account_status = tw_client.get_twitter_account_status(find_at)
                    if account_status == TWStatus.OK:
                        possible_at = find_at
                    elif account_status == TWStatus.SUSPENDED:
                        last_err = {"result": "error", "reason": Reasons.ACCOUNT_SUSPENDED, "suspended_account": find_at}
                        start_index = at_dnm - 1
                        continue
                    elif account_status == TWStatus.PROTECTED:
                        last_err = {"result": "error", "reason": Reasons.ACCOUNT_PROTECTED, "protected_account": find_at}
                        start_index = at_dnm - 1
                        continue
                    elif account_status == TWStatus.DNE:
                        last_err = {"result": "error", "reason": Reasons.ACCOUNT_DNE, "dne_account": find_at}
                        start_index = at_dnm - 1
                        continue

            # ------------------------------------------------
            if below_this:  # IF REPLY FOUND
                ah = below_this
            elif at is None:  # IF AT NOT FOUND
                ah = 0
            else:  # IF AT FOUND
                ah = at_dnm + 1

            search_list_tmp = []
            for s in split_loaded[ah:start_index + 1]:
                if not any(yasak in s for yasak in TextPrep.endhere):
                    # if len(s) >= 10 or '@' in s:
                    search_list_tmp.append(s.strip())
                else:
                    break

            search_list = []
            if len(search_list_tmp) > 1:
                for search_l in search_list_tmp:
                    if len(search_l) >= 10:
                        search_list.append(search_l)
            else:
                search_list = search_list_tmp

            search_list = ' '.join(search_list).split()
            # search_list = [x for x in search_list if '#' not in x and x]  # clear from hashtags and NoneTypes
            search_list = [x for x in search_list if x]  # clear from NoneTypes if any
            search_text = ' '.join(filter(lambda w: len(w) > 2, search_list))
            search_text = re.sub(' +', ' ', search_text)
            # ------------------------------------------------

            if not search_text:
                print("no text")
                last_err = {"result": "error", "reason": Reasons.NO_TEXT}
                start_index = at_dnm - 1
                continue

            if not possible_at and len(search_text.split()) <= 4:
                if start_index != 0:
                    last_err = {"result": "error", "reason": Reasons.TOO_SHORT_NO_AT}
                #print("too short and there is no at")
                start_index = at_dnm - 1
                continue

            possibe_search_text = []
            search_text_s = search_text.split()
            if len(search_text_s) < 45:
                possibe_search_text.append(search_text)

            slice_i = 2 if possible_at and not need_at else 1.5
            min_word_i = 3 if possible_at and not need_at else 5
            if len(search_text_s) >= min_word_i:
                n_1 = ceil(len(search_text_s) / slice_i)

                z_len_s = 100
                f_len_s = 0
                strs = []
                while z_len_s > min_word_i and f_len_s < 45:
                    strs += [' '.join(search_text_s[i:i + n_1]) for i in range(0, len(search_text_s), n_1)]
                    z_len_s = len(strs[-2].split())
                    f_len_s = len(strs[0].split())

                    if len(strs[-1].split()) < min_word_i:
                        strs.pop(-1)
                    n_1 -= 1

                strs.sort(key=lambda x: len(x.split()), reverse=True)

                for str_ in strs:
                    if len(str_.replace(' ', '')) < 8:
                        strs.remove(str_)

            else:
                strs = []

            possibe_search_text += strs

            tweet_search_models.append(TextPrep.tweet_search_model(possible_at=possible_at, possibe_search_text=possibe_search_text, no_at_variaton=False))
            total_detected_tweets += 1
            if not need_at and possible_at and 45 > len(search_text_s) > 5:
                tweet_search_models.append(TextPrep.tweet_search_model(possible_at=None, possibe_search_text=[search_text], no_at_variaton=True))
            start_index = at_dnm - 1

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models, "total_detected_tweets": total_detected_tweets}
        elif last_err:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}
