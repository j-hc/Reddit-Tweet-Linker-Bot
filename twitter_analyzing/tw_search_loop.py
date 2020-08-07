from .err_reasons import Reasons
from .twitter_client import tw_client


class TWSearch:
    @staticmethod
    def twitter_search(at_dene, possibe_search_text, lang):
        for search_text_use in possibe_search_text:
            if at_dene:
                print('twitter username: ' + at_dene)
            print('tweet text: ' + search_text_use)

            tweet_link = tw_client.search_tweet(tweet_text=search_text_use, from_whom=at_dene, lang=lang)
            if tweet_link is None:
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
            return {"result": "success", "username": tweeter, "twitlink": tweet_link, "atliatsiz": atsiz}

        return {"result": "error", "reason": Reasons.DEFAULT}
