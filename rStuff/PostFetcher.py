from .rUtils import rPost


class PostFetcher:
    def __init__(self, bot, subs=None, limit=50, sort_by='new', pagination=True, stop_if_saved=True, skip_if_nsfw=False,
                 before_or_after='before', pagination_param=None, multiname=None):
        assert any(before_or_after == ba for ba in ['before', 'after'])
        assert (subs is not None) != (multiname is not None)

        self.bot = bot

        self.subs = subs
        self.params = {"limit": limit}
        self.sort_by = sort_by
        self.pagination = pagination
        self.stop_if_saved = stop_if_saved
        self.skip_if_nsfw = skip_if_nsfw
        self.before_or_after = before_or_after

        self.last_fetched_ids = []
        if pagination_param is not None:
            self.params.update({self.before_or_after: self.pagination_param})
        self._fallback_index = 0
        if self.before_or_after == 'before':
            self._fallback_index_incrementer = 1
            self._pagination_post_indexer = 0
        elif self.before_or_after == 'after':
            self._pagination_post_indexer = self._fallback_index_incrementer = -1
        self.pagination_param = None

        if multiname is not None:
            self._uri = f"{self.bot.base}/user/{self.bot.bot_username}/m/{multiname}/"
        else:
            self._uri = f"{self.bot.base}/r/{'+'.join(self.subs)}/"
        self._uri += self.sort_by

    def fetch_posts(self):
        posts_req = self.bot.handled_req('GET', self._uri, params=self.params).json()
        posts = posts_req["data"]["children"]
        posts_len = posts_req["data"]["dist"]
        last_post_index = posts_len - 1

        for index, post in enumerate(posts):
            the_post = rPost(post)
            if the_post.id_ in self.last_fetched_ids or (self.stop_if_saved and the_post.is_saved):
                break
            if self.skip_if_nsfw and the_post.over_18:
                continue
            # self.bot.save_thing_by_id(the_post.id_)
            if self.stop_if_saved:
                if index == 0 and self.before_or_after == 'before':
                    self.bot.save_thing_by_id(the_post.id_)
                elif index == last_post_index and self.before_or_after == 'after':
                    self.bot.save_thing_by_id(the_post.id_)
            yield the_post

        if self.pagination:
            if self.before_or_after == "before":
                self.last_fetched_ids.extend([post['data']['name'] for post in posts[:15]])
            elif self.before_or_after == "after":
                self.last_fetched_ids.extend([post['data']['name'] for post in posts[-15:]])
            self.last_fetched_ids = self.last_fetched_ids[-15:]

            if posts_len != 0:
                self._fallback_index = 0
                self.pagination_param = posts[self._pagination_post_indexer]['data']['name']
            else:
                self.pagination_param = self.last_fetched_ids[self._fallback_index % 15]
                self._fallback_index += self._fallback_index_incrementer
            self.params.update({self.before_or_after: self.pagination_param})
