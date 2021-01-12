from .err_reasons import Reasons
from TwitterClient import TWStatus
import re
from math import ceil
from collections import namedtuple


class TextPrep:
    #  YES I KNOW THIS WHOLE THING IS UGLY ASF

    tw_username_dot = "·"
    three_dot = ".."
    re_endoftweet = re.compile(r'Twitter for|Translate Tweet|Tweeti Çevir|Tweet übersetzen|Twitter Web App|PM - |for (iOS|Android)| Translate from |Tweet your reply|\d{1,2}[.-]\d{1,2}[.-]\d{4}|'
                               r'Show this thread|Yanıtını Tweetle|dilinden Google tarafından|[0-9].*? Retweet.*?[0-9].*? Beğeni|Bu Tweet dizisini göster|Show replies|·|•|'
                               r'[0-9].*? Retweets.*?[0-9].*? Likes')
    re_twitterusername = re.compile(r"@([A-Za-z0-9_]{3,15})")
    re_replying = re.compile(r'antwort an|replying to|adlı kişiye|adlı kullanıcılara|kullanıcılara yanıt olarak|svar till|ve (diğer )*[0-9]+ kişiye|en réponse à|'
                             r'en respuesta a|em resposta a|daha yanıt olarak', re.IGNORECASE)
    re_only_letters_whitespace = re.compile('[^a-zA-Z ]')
    re_two_space = re.compile(' +')

    tweet_search_model = namedtuple("tweet_search_model", "possible_at possibe_search_text no_at_variaton")

    def __init__(self, tw_client):
        self.tw_client = tw_client

    def prep_text(self, text, need_at):
        # text = re.sub(r'\s?•\s?', " • ", text_)  # temporary dot replacer

        split_loaded = text.strip().split('\n')

        start_index = len(split_loaded) - 1
        tweet_search_models = []
        last_err = None
        while not start_index == -1:
            at = None
            below_this = None
            below_this_controller = 0
            for at_dnm in range(start_index, -1, -1):
                at_dnm_txt = str(split_loaded[at_dnm])
                if below_this is None:
                    pass
                elif below_this_controller >= 3:
                    break
                else:
                    below_this_controller += 1
                if bool(self.re_replying.search(at_dnm_txt)):
                    if not below_this:
                        below_this = at_dnm + 1
                elif at_dnm_txt.count('@') == 1:
                    if self.three_dot in at_dnm_txt and self.tw_username_dot not in at_dnm_txt:
                        at = None
                        if not below_this:
                            below_this = at_dnm + 1
                            break
                    else:
                        split_at = at_dnm_txt.split('@')

                        if self.tw_username_dot not in at_dnm_txt:
                            try:
                                rights_at = split_at[1].split(maxsplit=1)[1]
                                rights_at_l_b = len(self.re_only_letters_whitespace.sub('', rights_at)) >= 6
                            except IndexError:
                                rights_at_l_b = False
                            if rights_at_l_b:
                                print(at_dnm_txt)
                                continue

                            try:
                                lefts_at = split_at[0]
                                lefts_at_l_b = len(self.re_only_letters_whitespace.sub('', lefts_at)) > 29
                            except IndexError:
                                lefts_at_l_b = False
                            if lefts_at_l_b:
                                continue
                        tw_name_search_r = self.re_twitterusername.search(at_dnm_txt)
                        if bool(tw_name_search_r):
                            at = tw_name_search_r.group(1)
                            break
                        else:
                            continue
                elif self.three_dot in at_dnm_txt and self.tw_username_dot in at_dnm_txt:
                    below_this = at_dnm + 1
                    break
            if below_this_controller >= 3:
                at_dnm = below_this - 1
                pass

            if at is None:
                # print("@username gozukmuyor")
                possible_at = None
                if need_at:  # which means, called from a listing job
                    last_err = {"result": "error", "reason": Reasons.NO_AT}
                    start_index = at_dnm - 1
                    continue
            else:
                find_at = at
                account_status = self.tw_client.get_twitter_account_status(find_at)
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
                else:
                    raise NotImplementedError
            # ------------------------------------------------
            if below_this:  # IF REPLY FOUND
                ah = below_this
            elif at is None:  # IF AT NOT FOUND
                ah = 0
            else:  # IF AT FOUND
                ah = at_dnm + 1

            search_list_tmp = []
            for s in split_loaded[ah:start_index + 1]:
                if not bool(self.re_endoftweet.search(s)):
                    # if len(s) >= 10 or '@' in s:
                    search_list_tmp.append(s.strip())
                else:
                    break
            search_list = []
            if len(search_list_tmp) > 1:
                tmp_len_controller = 0
                for search_l in search_list_tmp:
                    if tmp_len_controller >= 4:
                        break
                    if not bool(self.re_only_letters_whitespace.sub('', search_l)):
                        tmp_len_controller += 1
                    elif len(search_l) >= 10:
                        search_list.append(search_l)
                    else:
                        tmp_len_controller += 1
            else:
                search_list = search_list_tmp
            search_list = ' '.join(search_list).split()
            search_list = filter(lambda w: not (w is None or all(x in w for x in ['.', '/'])), search_list)
            search_text = ' '.join(search_list)
            # search_text = ' '.join(filter(lambda w: len(w) > 2, search_list))
            search_text = self.re_two_space.sub(' ', search_text)
            # ------------------------------------------------

            if not search_text:
                # print("no text")
                last_err = {"result": "error", "reason": Reasons.DEFAULT}
                start_index = at_dnm - 1
                continue

            min_letters = 8 if possible_at and not need_at else 30
            if len(search_text.replace(' ', '')) <= min_letters:
                if start_index != 0 and last_err is not None and \
                        last_err['reason'] not in [Reasons.ACCOUNT_DNE, Reasons.ACCOUNT_SUSPENDED, Reasons.ACCOUNT_PROTECTED]:
                    last_err = {"result": "error", "reason": Reasons.TOO_SHORT_NO_AT}
                # print("too short and there is no at")
                start_index = at_dnm - 1
                continue

            possibe_search_text = []
            search_text_s = search_text.split()

            if len(search_text_s) < 45:
                possibe_search_text.append(search_text)

            slice_i = 2 if possible_at and not need_at else 1.8
            min_word_i = 3 if possible_at and not need_at else 5
            if len(search_text_s) >= min_word_i:
                n_1 = ceil(len(search_text_s) / slice_i)

                z_len_s = 100
                f_len_s = 0
                strs = []

                while z_len_s > min_word_i and f_len_s < 45:
                    addd = [' '.join(search_text_s[i:i + n_1]) for i in range(0, len(search_text_s), n_1)]
                    strs += addd
                    z_len_s = len(strs[-2].split())
                    f_len_s = len(strs[0].split())

                    # if len(strs[-1].split()) < min_word_i:
                    #     strs.pop(-1)
                    n_1 -= 1

                strs = set(strs)
                # strs = filter(lambda str_: len(str_.replace(' ', '')) >= min_letters, strs)
                strs = list(filter(lambda str_: len(str_.replace(' ', '')) >= min_letters and len(str_.split()) >= min_word_i, strs))
                strs.sort(key=lambda x: len(x.split()), reverse=True)
            else:
                strs = []

            possibe_search_text += strs

            tweet_search_models.append(self.tweet_search_model(possible_at=possible_at, possibe_search_text=possibe_search_text, no_at_variaton=False))
            if not need_at and possible_at and 45 > len(search_text_s) > 5:
                tweet_search_models.append(self.tweet_search_model(possible_at=None, possibe_search_text=[search_text], no_at_variaton=True))
            start_index = at_dnm - 1

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models}
        elif last_err:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}
