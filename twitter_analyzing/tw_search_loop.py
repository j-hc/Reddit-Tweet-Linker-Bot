from .err_reasons import Reasons
from .twitter_client import tw_client
import sys
sys.path.append('..')
from db import tweet_database


class TWSearch:
    @staticmethod
    def twitter_search(at_dene, possibe_search_text, lang):
        for search_text_use in possibe_search_text:
            if at_dene:
                print('twitter username: ' + at_dene)
            print('tweet text: ' + search_text_use)

            tweet_dict = tw_client.search_tweet(tweet_text=search_text_use, from_whom=at_dene, lang=lang)
            tweet_link = tweet_dict.get('link')
            user_id = tweet_dict.get('user_id')
            if tweet_link is None:
                db_query = tweet_database.a_query(user_id, search_text_use)
                if db_query:
                    return {"result": "success_db", "db_backup_link": db_query[0]}
                continue
            else:
                print('\r\nFound yay: ' + tweet_link)
            if at_dene is None:
                found_tweetr = tweet_link.split('/')[3]
                tweeter = found_tweetr
                atsiz = True
            else:
                tweeter = at_dene
                atsiz = False
            return {"result": "success", "username": tweeter, "twitlink": tweet_link, "atliatsiz": atsiz, "user_id": user_id}

        return {"result": "error", "reason": Reasons.DEFAULT}
