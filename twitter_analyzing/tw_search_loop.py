from .err_reasons import Reasons
# from db import tweet_database


class TWSearch:
    def __init__(self, tw_client):
        self.tw_client = tw_client

    def twitter_search(self, searching_for_tweets, lang):
        if len([tw for tw in searching_for_tweets if not tw.no_at_variaton]) == 2:
            results_l = []
            for searching_for_tweet in reversed(searching_for_tweets):
                if searching_for_tweet.no_at_variaton:
                    continue
                result_t = self._search_t(searching_for_tweet, lang)
                if result_t is not None:
                    if result_t[1]:
                        return result_t[0]
                    else:
                        results_l.append(result_t[0])
            if bool(results_l):
                return results_l[-1]
        else:
            for searching_for_tweet in searching_for_tweets:
                result_t = self._search_t(searching_for_tweet, lang)
                if result_t is not None:
                    return result_t[0]

        return {"result": "error", "reason": Reasons.DEFAULT}

    def _search_t(self, searching_for_tweet, lang):
        at_dene = searching_for_tweet.possible_at
        possibe_search_text = searching_for_tweet.possibe_search_text[:55]  # max first 55 tweet text

        for search_text_use in possibe_search_text:
            if at_dene:
                print('twitter username: ' + at_dene)
            print('tweet text: ' + search_text_use)

            exact_phrase = True if at_dene is None else False
            tweet_dict = self.tw_client.search_tweet(tweet_text=search_text_use, from_whom=at_dene, lang=lang, exact_phrase=exact_phrase)
            tweet_link = tweet_dict.get('link')
            user_id = tweet_dict.get('user_id')
            b_could_be_quote = tweet_dict.get('b_could_be_quote')

            if tweet_link is None:
                continue
            # if tweet_link is None:
            #     db_query = tweet_database.a_query(user_id, search_text_use)
            #     if db_query:
            #         return {"result": "success_db", "db_backup_link": db_query[0]}
            #     continue

            print('\r\nFound yay: ' + tweet_link)
            if at_dene is None:
                found_tweetr = tweet_link.split('/')[3]
                tweeter = found_tweetr
                atsiz = True
            else:
                tweeter = at_dene
                atsiz = False

            tweet_res = {"result": "success", "username": tweeter, "twitlink": tweet_link, "atliatsiz": atsiz,
                         "user_id": user_id, "found_index": possibe_search_text.index(search_text_use), "no_at_variaton": searching_for_tweet.no_at_variaton}
            return tweet_res, b_could_be_quote

        return None
