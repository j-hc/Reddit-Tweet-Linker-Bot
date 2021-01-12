from .err_reasons import Reasons
from TwitterClient import TWStatus
import re
from math import ceil
from collections import namedtuple


class TextPrep:
    #  YES I KNOW THIS WHOLE THING IS UGLY ASF

    re_replying2 = re.compile(r'Antwort an|Replying to|adlı kişiye|adlı kullanıcılara|kullanıcılara yanıt olarak|olarak|svar till|ve diğer [0-9]+ kişiye|En réponse à|'
                              r'En respuesta a')
    re_endoftweet2 = re.compile(r'Twitter for|Translate Tweet|Tweeti Çevir|Twitter Web App|PM - |for (iOS|Android)| Translate from |Tweet your reply|\d{1,2}[.-]\d{1,2}[.-]\d{4}|'
                                r'Show this thread|Yanıtını Tweetle|dilinden Google tarafından|[0-9].*? Retweet.*?[0-9].*? Beğeni|Bu Tweet dizisini göster|'
                                r'[0-9].*? Retweets.*?[0-9].*? Likes')
    re_twitterusername2 = re.compile(r"@([A-Za-z0-9_]{4,15}|ntv)")

    re_endoftweet = re.compile(r'Twitter for|Translate Tweet|Tweeti Çevir|Twitter Web App|PM - |(20|19|18) - |for (iOS|Android)| · | Translate from |Tweet your reply|'
                               r'Show this thread|Yanıtını Tweetle| - (1|2|3)|dilinden Google tarafından|•|[0-9].*? Retweet.*?[0-9].*? Beğeni|Bu Tweet dizisini göster| PM -')
    re_twitterusername = re.compile(r"[A-Za-z0-9_]{4,15}|ntv")  # how tf ntv got a 3 chars username lol
    re_replying = re.compile(r'antwort an|replying to|adlı kişiye|adlı kullanıcılara|kullanıcılara yanıt olarak|olarak|svar till|ve diğer [0-9]+ kişiye|en réponse à|'
                             r'en respuesta a')

    re_two_space = re.compile(' +')

    tweet_search_model = namedtuple("tweet_search_model", "possible_at possibe_search_text no_at_variaton")
    tweet_block = namedtuple("tweet_block", "tweeter_box tweet_text_box")

    def __init__(self, tw_client):
        self.tw_client = tw_client

    def _create_tweet_blocks(self, ocr_data):
        blocks = ocr_data['data']['blocks']

        tweet_blocks = []
        prev_y = -100
        append_trailing_boxes = False
        append_trailing_boxes_r = False
        tweet_text = None
        for block in blocks:
            # if abs(block['y'] - prev_y) <= 20:
            #     continue
            # prev_y = block['y']

            boxes = block['boxes']
            boxes_last_index = len(boxes) - 1

            tweet_text = []
            for index, box in enumerate(boxes):
                box_text = box['text']
                text_color_r = box['textColor']['r']

                if bool(TextPrep.re_endoftweet2.search(box_text)):
                    print("yyyyyyyyy", end=' ')
                    print(box_text)
                    break

                if bool(TextPrep.re_replying2.search(box_text)) and text_color_r < 200:
                    print("zzzzzzzzz", end=' ')
                    print(box_text)
                    continue

                if "@" in box_text or ' • ' in box_text:
                    tweeter_box = None
                    if '…' not in box_text:
                        tweeter_box_try = TextPrep.re_twitterusername2.search(box_text)
                        if bool(tweeter_box_try):
                            tweeter_box = tweeter_box_try.group(1)
                    print("aaaaaaaaaaaa", end=' ')
                    print(tweeter_box)
                    print(box_text)
                    append_trailing_boxes = True
                elif append_trailing_boxes or (append_trailing_boxes_r and
                                               ("@" not in box_text or all(xx in box_text for xx in ['…', ' • '])) and
                                               not box_text.replace('.', '').replace(',', '').isdigit()):
                    tweet_text.append(box_text)
                    if index == boxes_last_index:
                        xx = TextPrep.tweet_block(tweeter_box=tweeter_box, tweet_text_box=' '.join(tweet_text))
                        tweet_blocks.append(xx)
                        print(xx)
                        append_trailing_boxes = False
                        append_trailing_boxes_r = False
                elif not 100 < text_color_r < 170 and not box_text.replace('.', '').replace(',', '').isdigit():
                    print("ccccccccccc", end=' ')
                    print(box_text)
                    tweeter_box = None
                    append_trailing_boxes_r = True
                    tweet_text.append(box_text)
                else:
                    print("xxxxxxx", end=' ')
                    print(box_text)
        if (append_trailing_boxes or append_trailing_boxes_r) and bool(tweet_text):
            tweet_blocks.append(TextPrep.tweet_block(tweeter_box=tweeter_box, tweet_text_box=' '.join(tweet_text)))
        print()
        return tweet_blocks

    def prep_text2(self, ocr_data, need_at):
        tweet_blocks = self._create_tweet_blocks(ocr_data)[:5]  # only last 5

        if not bool(tweet_blocks) and need_at:
            return {"result": "error", "reason": Reasons.NO_AT}

        last_err = None
        tweet_search_models = []
        for tweet_block in reversed(tweet_blocks):
            print(tweet_block)

            at_to_be_used = None
            if tweet_block.tweeter_box is not None:
                account_status = self.tw_client.get_twitter_account_status(tweet_block.tweeter_box)
                if account_status == TWStatus.OK:
                    at_to_be_used = tweet_block.tweeter_box
                elif account_status == TWStatus.SUSPENDED:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_SUSPENDED, "suspended_account": tweet_block.tweeter_box}
                    continue
                elif account_status == TWStatus.PROTECTED:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_PROTECTED, "protected_account": tweet_block.tweeter_box}
                    continue
                elif account_status == TWStatus.DNE:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_DNE, "dne_account": tweet_block.tweeter_box}
                    continue
            elif need_at:
                last_err = {"result": "error", "reason": Reasons.NO_AT}
                continue

            tweet_text_filter = [x for x in tweet_block.tweet_text_box.split() if not all(likelylink in x for likelylink in ['/', '…'])]
            tweet_text_filter = ' '.join(filter(lambda w: len(w) > 2, tweet_text_filter))
            tweet_text_filter = TextPrep.re_two_space.sub(' ', tweet_text_filter)

            if not bool(tweet_text_filter):
                # print("no text prepped")
                last_err = {"result": "error", "reason": Reasons.DEFAULT}
                continue

            if at_to_be_used is None and len(tweet_text_filter.split()) <= 4:
                # print("too short and there is no at")
                last_err = {"result": "error", "reason": Reasons.TOO_SHORT_NO_AT}
                continue

            possibe_search_text = []
            search_text_s = tweet_text_filter.split()

            if len(search_text_s) < 45:
                possibe_search_text.append(tweet_text_filter)

            slice_i = 2 if bool(at_to_be_used) and not need_at else 1.8
            min_word_i = 3 if bool(at_to_be_used) and not need_at else 5
            strs = []
            if len(search_text_s) >= min_word_i:
                n_1 = ceil(len(search_text_s) / slice_i)

                z_len_s = 100
                f_len_s = 0

                while z_len_s > min_word_i and f_len_s < 45:
                    strs += [' '.join(search_text_s[i:i + n_1]) for i in range(0, len(search_text_s), n_1)]
                    z_len_s = len(strs[-2].split())
                    f_len_s = len(strs[0].split())

                    if len(strs[-1].split()) < min_word_i:
                        strs.pop(-1)
                    n_1 -= 1

                strs = set(strs)
                strs = list(filter(lambda str_: len(str_.replace(' ', '')) >= 8, strs))
                strs.sort(key=lambda x: len(x.split()), reverse=True)

            possibe_search_text += strs

            tweet_search_models.append(TextPrep.tweet_search_model(possible_at=at_to_be_used, possibe_search_text=possibe_search_text, no_at_variaton=False))
            if not need_at and at_to_be_used and 45 > len(search_text_s) > 5:
                tweet_search_models.append(TextPrep.tweet_search_model(possible_at=None, possibe_search_text=[tweet_block.tweet_text_box], no_at_variaton=True))

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models}
        elif last_err is not None:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}

    def prep_text(self, text_, need_at):
        text = re.sub(r'\s?•\s?', " • ", text_)  # temporary dot replacer

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
                at_dnm_txt_low = at_dnm_txt.lower()

                if below_this is None:
                    pass
                elif below_this_controller >= 3:
                    break
                else:
                    below_this_controller += 1

                if "@" in at_dnm_txt:
                    if bool(TextPrep.re_replying.search(at_dnm_txt_low)):
                        below_this = at_dnm + 1
                    else:
                        extrct_at = at_dnm_txt.split('@')[1].split()
                        if bool(extrct_at):
                            if len(extrct_at) >= 1:
                                if len(' '.join(extrct_at[1:])) < 7 or ' • ' in at_dnm_txt:
                                    at = extrct_at[0]
                                    break
                                else:
                                    continue
                            else:
                                at = extrct_at[0]
                                break
                elif '…' in at_dnm_txt and ' • ' in at_dnm_txt:
                    below_this = at_dnm + 1
                    break

            if at is None:
                # print("@username gozukmuyor")
                possible_at = None
                if need_at:  # which means, called from a listing job
                    last_err = {"result": "error", "reason": Reasons.NO_AT}
                    start_index = at_dnm - 1
                    continue
            else:
                find_at = at
                if not bool(TextPrep.re_twitterusername.fullmatch(find_at)):
                    if not below_this:
                        below_this = at_dnm + 1
                    possible_at = None
                    if need_at:  # which means, called from a listing job
                        last_err = {"result": "error", "reason": Reasons.NO_AT}
                        start_index = at_dnm - 1
                        continue
                else:
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

            # ------------------------------------------------
            if below_this:  # IF REPLY FOUND
                ah = below_this
            elif at is None:  # IF AT NOT FOUND
                ah = 0
            else:  # IF AT FOUND
                ah = at_dnm + 1

            search_list_tmp = []
            for s in split_loaded[ah:start_index + 1]:
                if not bool(TextPrep.re_endoftweet.search(s)):
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
            search_list = [x for x in search_list if x and '…' not in x]  # clear from NoneTypes and threedots if any
            search_text = ' '.join(filter(lambda w: len(w) > 2, search_list))
            search_text = TextPrep.re_two_space.sub(' ', search_text)
            # ------------------------------------------------

            if not search_text:
                print("no text")
                last_err = {"result": "error", "reason": Reasons.DEFAULT}
                start_index = at_dnm - 1
                continue

            if not possible_at and len(search_text.split()) <= 4:
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
                    strs += [' '.join(search_text_s[i:i + n_1]) for i in range(0, len(search_text_s), n_1)]
                    z_len_s = len(strs[-2].split())
                    f_len_s = len(strs[0].split())

                    if len(strs[-1].split()) < min_word_i:
                        strs.pop(-1)
                    n_1 -= 1

                strs = set(strs)
                strs = list(filter(lambda str_: len(str_.replace(' ', '')) >= 8, strs))
                strs.sort(key=lambda x: len(x.split()), reverse=True)

            else:
                strs = []

            possibe_search_text += strs
            tweet_search_models.append(TextPrep.tweet_search_model(possible_at=possible_at, possibe_search_text=possibe_search_text, no_at_variaton=False))
            if not need_at and possible_at and 45 > len(search_text_s) > 5:
                tweet_search_models.append(TextPrep.tweet_search_model(possible_at=None, possibe_search_text=[search_text], no_at_variaton=True))
            start_index = at_dnm - 1

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models}
        elif last_err:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}
