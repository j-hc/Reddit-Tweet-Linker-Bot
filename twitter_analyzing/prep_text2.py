from .err_reasons import Reasons
from TwitterClient import TWStatus
import re
from math import ceil
from dataclasses import dataclass


@dataclass
class _TweetSearchModel:
    possible_at: str = None
    possibe_search_text: list = None
    no_at_variaton: bool = False


@dataclass
class _TweetBlock:
    tweeter_box: str = None
    tweet_text_box: str = None


class TextPrep:
    #  YES I KNOW THIS WHOLE THING IS UGLY ASF

    tw_username_dot = "·"
    three_dot = ".."  # … for yandex ocr

    re_replying2 = re.compile(
        r'Antwort an|Replying to|adlı kişiye|adlı kullanıcı(lara|ya)|yanıt olarak|svar till|ve diğer [0-9]+ kişiye'
        r'|En réponse à|En respuesta a|@(.*?), @(.*?) (ve|and) @(.*?)|Em resposta a')

    re_endoftweet2 = re.compile(
        r'Twitter for|Translate Tweet|Tweeti Çevir|Twitter Web App|PM - |for (iOS|Android)| Translate from '
        r'|\d{1,2}[/.-]\d{1,2}[/.-]\d{1,4} [·-]|Show this thread|dilinden Google tarafından'
        r'|[0-9].*? Retweet.*?[0-9].*? Beğeni|Bu Tweet dizisini göster|Tweet etkinliğini görüntüle'
        r'|[0-9].*? Retweets.*?[0-9].*? Likes|Show replies|\d{2}:\d{2}\s?(?:AM|PM)* ([·-] )?\d{1,2}| ♡ ')

    re_twitterusername2 = re.compile(r"@([A-Za-z0-9_]{3,17})")

    re_two_space = re.compile(' +')
    re_only_letters_whitespace = re.compile('[^a-zA-Z!?ışçöğüİŞÇÖĞÜ ]')

    def __init__(self, tw_client):
        self.max_word_x_diff = None
        self.max_line_x_diff = None
        self.max_line_y_diff = None
        self.max_word_y_diff = None
        self.minus_y_for_chars_with_tails = None
        self.plus_y_for_lil_dot = None
        self.tw_client = tw_client

        self.li = False
        self.bl = False
        self.tw = False

    def _print_d(self, p=''):
        if self.li:
            print(p)

    def _print_t(self, p=''):
        if self.tw:
            print(p)

    def _print_b(self, p=''):
        if self.bl:
            print(p)

    def extract_text_blocks(self, ocr_data, return_raw_blocks=True):
        def _truncated_float(flt, _f='3'):
            _f_ = f'%.{_f}f'
            return float(_f_ % flt)

        self.minus_y_for_chars_with_tails = 5.0

        text_annotations = ocr_data['textAnnotations'][1:]
        vertice_texts = []
        id_incrementer = 0
        total_y_diff_of_words = 0
        for text_annotation in text_annotations:
            vertices = text_annotation['boundingPoly']['vertices']
            text = text_annotation['description']
            box = []
            for vertic_i, vertice in enumerate(reversed(vertices)):
                x_val = vertice.get('x', 0)
                y_val = vertice.get('y', 0)

                if any(lt in text for lt in ['g', 'p', 'y', 'ğ', 'ç', 'ş']) and (vertic_i == 0 or vertic_i == 1):
                    y_val -= self.minus_y_for_chars_with_tails

                box.append((x_val, y_val))
            total_y_diff_of_words += abs((box[0][1] + box[1][1]) - (box[2][1] + box[3][1])) / 2
            vertice_texts.append((text, tuple(box), id_incrementer))
            id_incrementer += 1

        avg_y_diff_of_words = total_y_diff_of_words / id_incrementer

        self.max_word_y_diff = 0.23 * avg_y_diff_of_words + 7.48
        self.max_line_y_diff = 1.6 * avg_y_diff_of_words + 2.35  # 1.6 * avg_y_diff_of_words + 2.35
        self.max_word_x_diff = 1.15 * avg_y_diff_of_words + 41.5  # 0.809 * avg_y_diff_of_words + 7.39  # 1.15 * avg_y_diff_of_words + 41.5
        self.max_line_x_diff = 1.24 * avg_y_diff_of_words + 21.0  # 0.3618 * avg_y_diff_of_words + 19.53

        lines = []
        red_references = set()
        elem_id_incrementer = 0
        for vertice_text_base in vertice_texts:
            if vertice_text_base[2] in red_references:
                continue
            red_references.add(vertice_text_base[2])

            nearyby_y_vals = [vertice_text_base]
            last_added = vertice_text_base
            self._print_d(f"base: {vertice_text_base}")
            for vertice_text in vertice_texts:
                if vertice_text[2] in red_references:
                    continue

                box = vertice_text[1]
                last_elem = last_added
                last_elem_box_of_line = last_elem[1]

                avg_right_x_val_of_last_elem = (last_elem_box_of_line[1][0] + last_elem_box_of_line[2][0]) / 2.0
                avg_left_x_val_of_last_elem = (last_elem_box_of_line[0][0] + last_elem_box_of_line[3][0]) / 2.0
                avg_right_x_val_of_ref = (box[1][0] + box[2][0]) / 2.0
                avg_left_x_val_of_ref = (box[0][0] + box[3][0]) / 2.0
                right_left_diff = abs(avg_right_x_val_of_last_elem - avg_left_x_val_of_ref)
                left_right_diff = abs(avg_left_x_val_of_last_elem - avg_right_x_val_of_ref)
                check_x_diff = right_left_diff if right_left_diff < left_right_diff else left_right_diff

                avg_bottom_y_val_of_last_elem = (last_elem_box_of_line[0][1] + last_elem_box_of_line[1][1]) / 2.0
                avg_bottom_y_val_ref = (box[0][1] + box[1][1]) / 2.0
                check_y_diff = abs(avg_bottom_y_val_of_last_elem - avg_bottom_y_val_ref)

                new_y_check = None
                new_x_check = None
                if any(vertice_text[0] == lt or last_elem[0] == lt for lt in [self.tw_username_dot, '-']):
                    new_y_check = self.max_word_y_diff + 11.0
                    new_x_check = self.max_word_x_diff + 6.0
                    is_y_elg = check_y_diff < new_y_check
                    is_x_elg = check_x_diff < new_x_check
                else:
                    is_y_elg = check_y_diff < self.max_word_y_diff
                    is_x_elg = check_x_diff < self.max_word_x_diff

                self._print_d(f"ref: {vertice_text}")
                self._print_d(f"last elem {nearyby_y_vals[-1]}")
                self._print_d(f"x check: {avg_left_x_val_of_last_elem} - {avg_right_x_val_of_ref}")
                self._print_d(f"y check: {avg_bottom_y_val_of_last_elem} - {avg_bottom_y_val_ref}")
                self._print_d(f"y {check_y_diff}<{self.max_word_y_diff if new_y_check is None else new_y_check} "
                              f": x {check_x_diff} < {self.max_word_x_diff if new_x_check is None else new_x_check}")
                if is_y_elg and is_x_elg:
                    self._print_d("eklendi")
                    self._print_d()
                    nearyby_y_vals.append(vertice_text)
                    red_references.add(vertice_text[2])
                    last_added = vertice_text
            nearyby_y_vals.sort(key=lambda x: x[1][0][0])
            self._print_d()

            nearyby_y_vals_without_dot = list(filter(lambda w: w != self.tw_username_dot, nearyby_y_vals))
            nearyby_y_vals_without_dot_len = len(nearyby_y_vals_without_dot)

            total_bottom_y = 0
            for box_y in nearyby_y_vals_without_dot:
                total_bottom_y += (box_y[1][0][1] + box_y[1][1][1]) / 2.0
            avg_bottom_y_of_line = _truncated_float(total_bottom_y / nearyby_y_vals_without_dot_len)

            total_top_y = 0
            for box_y in nearyby_y_vals_without_dot:
                total_top_y += (box_y[1][2][1] + box_y[1][3][1]) / 2.0
            avg_top_y_of_line = _truncated_float(total_top_y / nearyby_y_vals_without_dot_len)

            avg_left_x_of_line = _truncated_float((nearyby_y_vals[0][1][0][0] + nearyby_y_vals[0][1][3][0]) / 2.0)

            line_box = (avg_left_x_of_line, avg_bottom_y_of_line, avg_top_y_of_line)
            line_text = ' '.join([str(txt[0]) for txt in nearyby_y_vals])
            lines.append((line_text, line_box, elem_id_incrementer))
            elem_id_incrementer += 1

        lines.sort(key=lambda x: x[1][1])

        blocks = []
        red_references = set()
        for line_base in lines:
            if line_base[2] in red_references:
                continue
            red_references.add(line_base[2])
            box_base = line_base[1]
            avg_left_x_of_line_base = box_base[0]

            line_truncated = line_base[:2]
            same_parag_lines = [line_base[:2]]
            last_added = line_truncated

            self._print_b(f"base: {line_base}")
            for line in lines:
                if line[2] in red_references:
                    continue
                box = line[1]
                line_last_elem = last_added

                last_elem_y_of_top = line_last_elem[1][2]
                last_elem_y_of_bottom = line_last_elem[1][1]
                ref_elem_y_of_top = box[2]
                ref_elem_y_of_bottom = box[1]

                avg_left_x_of_line = box[0]

                top_bottom_diff = abs(ref_elem_y_of_bottom - last_elem_y_of_top)
                bottom_top_diff = abs(ref_elem_y_of_top - last_elem_y_of_bottom)

                bottom_top_min_diff = top_bottom_diff if top_bottom_diff < bottom_top_diff else bottom_top_diff
                check_left_x_diff = abs(avg_left_x_of_line_base - avg_left_x_of_line)
                self._print_b(f"last elem {line_last_elem}")
                self._print_b(f"ref: {line}")
                self._print_b(f"y {ref_elem_y_of_top} - {last_elem_y_of_bottom}")
                self._print_b(f"x {avg_left_x_of_line_base} - {avg_left_x_of_line}")
                self._print_b(
                    f"y {bottom_top_min_diff} < {self.max_line_y_diff} : x {check_left_x_diff}<{self.max_line_x_diff}")
                if check_left_x_diff < self.max_line_x_diff and bottom_top_min_diff < self.max_line_y_diff:
                    red_references.add(line[2])
                    line_truncated_s = line[:2]
                    same_parag_lines.append(line_truncated_s)
                    last_added = line_truncated_s
                    self._print_b("eklendi")
                    self._print_b()
            same_parag_lines.sort(key=lambda x: x[1][1])
            self._print_b()
            top_y_of_parag = _truncated_float(same_parag_lines[0][1][2])
            bottom_y_of_parag = _truncated_float(same_parag_lines[-1][1][1])
            avg_left_x_of_parag = _truncated_float(float(sum([box_x[1][0] for box_x in same_parag_lines]) / len(same_parag_lines)))
            parag_box = (avg_left_x_of_parag, bottom_y_of_parag, top_y_of_parag)
            blocks.append((tuple(same_parag_lines), parag_box))
        blocks.sort(key=lambda x: (x[1][1] + x[1][2]) / 2.0)
        if return_raw_blocks:
            return blocks
        else:
            return ['\n'.join([txt[0] for txt in x]) for x in [blc[0] for blc in blocks]]

    def create_tweet_blocks(self, text_blocks):
        append_trailing_lines = False
        tweet_blocks = []
        tweet_text = []
        last_ending = True
        only_tweeter_box_same_line = False
        first_box_added = False
        tweeter_box = None
        first_skipped_line = None
        last_line_left_x = None
        tweeter_bottom_y = 0
        added_block_indexes = set()
        tweeter_box_index = -1
        for block_i, text_block in enumerate(text_blocks):
            lines_it = text_block[0]
            lines_last_index = len(lines_it) - 1
            for line_index, line in enumerate(lines_it):
                line_text = line[0]
                line_box = line[1]
                current_line_left_x = line_box[0]
                current_bottom_y = line_box[1]

                if line_text == self.tw_username_dot:
                    continue

                if tweeter_box_index != block_i and append_trailing_lines and abs(tweeter_bottom_y - current_bottom_y) < self.max_word_y_diff:
                    self._print_t(f"is same line {line_text} | {tweeter_bottom_y}-{current_bottom_y}={abs(tweeter_bottom_y - current_bottom_y)}<{self.max_word_y_diff}")
                    continue

                if bool(self.re_replying2.search(line_text)) or line_text == 'olarak':
                    self._print_t(f"line_text replying: {line_text}")
                    tweet_text.clear()
                    if not append_trailing_lines:
                        tweeter_box = None
                        append_trailing_lines = True
                    continue

                ending = True if bool(self.re_endoftweet2.search(line_text)) else False
                if (not append_trailing_lines or first_box_added) \
                        and (line_text.count('@') == 1
                             or (self.tw_username_dot in line_text
                                 and not ending
                                 and len(line_text.split(self.tw_username_dot)[0]) >= 1)):
                    if bool(tweet_text):
                        tweet_block2append = _TweetBlock(tweeter_box=tweeter_box, tweet_text_box=' '.join(tweet_text))
                        if block_i not in added_block_indexes:
                            tweet_blocks.append(tweet_block2append)
                            first_skipped_line = None
                            self._print_t(tweet_block2append)
                            self._print_t()
                            if first_box_added:
                                block_i_to_add = block_i - 1
                            else:
                                block_i_to_add = block_i
                            added_block_indexes.add(block_i_to_add)
                    tweet_text.clear()

                    if line_text[0] != '@' and '@' in line_text:
                        only_tweeter_box_same_line = True
                        tweeter_left_x = current_line_left_x
                    else:
                        only_tweeter_box_same_line = False

                    first_box_added = False
                    tweeter_box = None
                    tweet_text.clear()
                    try:
                        tweeter_line_text = line_text.split('@')[1].split()[0]
                    except:
                        tweeter_line_text = line_text

                    if not (self.three_dot in tweeter_line_text or ('.' in tweeter_line_text and self.tw_username_dot in line_text)):
                        tweeter_box_try = self.re_twitterusername2.search(line_text)
                        if bool(tweeter_box_try):
                            tweeter_box = tweeter_box_try.group(1)
                    tweeter_bottom_y = line_box[1]
                    tweeter_box_index = block_i

                    self._print_t(f"found: {line_text}")
                    self._print_t()
                    append_trailing_lines = True
                elif append_trailing_lines:
                    if line_index == lines_last_index:
                        self._print_t("first box added")
                        first_box_added = True

                    if only_tweeter_box_same_line and 4.5 * self.max_line_x_diff > abs(current_line_left_x - tweeter_left_x) > 1.15 * self.max_line_x_diff:
                        self._print_t(f"only_tweeter_box_same_line skipped {line_text}")
                        if not bool(first_skipped_line):
                            first_skipped_line = line_text
                        continue

                    if not ending:
                        if len(self.re_only_letters_whitespace.sub('', line_text)) > 4:
                            self._print_t(f"eklendi: {line_text} {len(self.re_only_letters_whitespace.sub('', line_text))}")
                            tweet_text.append(line_text)
                        elif line_index != lines_last_index:
                            self._print_t(f"skipped2: {line_text} {self.re_only_letters_whitespace.sub('', line_text)}")
                            continue
                        else:
                            self._print_t(f"skipped3: {line_text} {self.re_only_letters_whitespace.sub('', line_text)}")
                            pass
                    try:
                        next_block_left_x = text_blocks[block_i + 1][1][0]
                        next_block_top_y = text_blocks[block_i + 1][1][2]
                        continue_to_next_block = abs(current_line_left_x - next_block_left_x) < 0.9 * self.max_line_x_diff \
                                                 and abs(next_block_top_y - current_bottom_y) < 2.35 * self.max_line_y_diff
                    except:
                        continue_to_next_block = False
                    if (not continue_to_next_block and line_index == lines_last_index) or ending:
                        self._print_t(f"ending or: {line_text}")
                        if bool(tweet_text) or bool(first_skipped_line):
                            if not bool(tweet_text):
                                tweet_text_box_v = first_skipped_line
                            else:
                                tweet_text_box_v = ' '.join(tweet_text)
                            tweet_block2append = _TweetBlock(tweeter_box=tweeter_box, tweet_text_box=tweet_text_box_v)
                            if block_i not in added_block_indexes:
                                tweet_blocks.append(tweet_block2append)
                                first_skipped_line = None
                                self._print_t(tweet_block2append)
                                self._print_t()
                                added_block_indexes.add(block_i)
                                only_tweeter_box_same_line = False
                        tweet_text.clear()
                        append_trailing_lines = False
                        break
                    else:
                        self._print_t(f"continue_to_next_block: {continue_to_next_block}")
                elif ending and not last_ending and last_line_left_x is not None and abs(current_line_left_x - last_line_left_x) < self.max_line_x_diff:
                    block_i_to_extract_text_from = block_i - 1
                    if line_index != 0 and all(indx not in added_block_indexes for indx in [block_i, block_i - 1]):
                        self._print_t(f"ending l: {line_text}")
                        lines_of_possible_tweet = lines_it[:line_index]
                        lines_text_only = ' '.join([li[0] for li in lines_of_possible_tweet
                                                    if self.re_endoftweet2.search(
                                li[0]) is None and self.re_replying2.search(li[0]) is None])
                        tweet_block2append = _TweetBlock(tweet_text_box=lines_text_only)
                        tweet_blocks.insert(0, tweet_block2append)
                        added_block_indexes.add(block_i)
                    elif block_i != 0 and all(indx not in added_block_indexes for indx in
                                              [block_i_to_extract_text_from, block_i_to_extract_text_from - 1]):
                        self._print_t(f"ending b: {line_text}")
                        lines_of_possible_tweet = text_blocks[block_i_to_extract_text_from][0]
                        lines_text_only = ' '.join([li[0] for li in lines_of_possible_tweet
                                                    if self.re_endoftweet2.search(
                                li[0]) is None and self.re_replying2.search(li[0]) is None])
                        tweet_block2append = _TweetBlock(tweet_text_box=lines_text_only)
                        tweet_blocks.insert(0, tweet_block2append)
                        added_block_indexes.add(block_i_to_extract_text_from)
                last_ending = ending
                last_line_left_x = current_line_left_x
        if not bool(tweet_blocks) and len(text_blocks) >= 1:
            max_length_text = ""
            max_length_text_l = 0
            for txt_blck in text_blocks:
                block_text = ' '.join([li[0] for li in txt_blck[0]])
                if bool(self.re_endoftweet2.search(block_text)):
                    continue
                block_text_l = len(block_text)
                if block_text_l > max_length_text_l:
                    max_length_text = block_text
                    max_length_text_l = block_text_l
            if max_length_text_l != 0:
                tweet_blocks = [_TweetBlock(tweet_text_box=max_length_text)]
        return tweet_blocks

    def prep_text(self, ocr_data, need_at):
        text_blocks = self.extract_text_blocks(ocr_data)
        tweet_blocks = self.create_tweet_blocks(text_blocks)[:5]  # only last 5

        if not bool(tweet_blocks):
            return {"result": "error", "reason": Reasons.DEFAULT}
        last_err = None
        tweet_search_models = []
        for tweet_block in reversed(tweet_blocks):
            at_to_be_used = None
            if tweet_block.tweeter_box is not None:
                account_status = self.tw_client.get_twitter_account_status(tweet_block.tweeter_box)
                if account_status == TWStatus.OK:
                    at_to_be_used = tweet_block.tweeter_box
                elif account_status == TWStatus.SUSPENDED:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_SUSPENDED,
                                "suspended_account": tweet_block.tweeter_box}
                    continue
                elif account_status == TWStatus.PROTECTED:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_PROTECTED,
                                "protected_account": tweet_block.tweeter_box}
                    continue
                elif account_status == TWStatus.DNE:
                    last_err = {"result": "error", "reason": Reasons.ACCOUNT_DNE,
                                "dne_account": tweet_block.tweeter_box}
                    continue
            elif need_at:
                last_err = {"result": "error", "reason": Reasons.NO_AT}
                continue

            search_list = tweet_block.tweet_text_box.split()
            tweet_text_filter = filter(lambda w: not (w is None or all(x in w for x in ['.', '/'])), search_list)
            tweet_text_filter = ' '.join(tweet_text_filter)
            # tweet_text_filter = ' '.join(filter(lambda w: len(w) > 2, tweet_text_filter))
            tweet_text_filter = self.re_two_space.sub(' ', tweet_text_filter)

            if not bool(tweet_text_filter):
                # no text prepped
                last_err = {"result": "error", "reason": Reasons.DEFAULT}
                continue

            min_letters = 7 if at_to_be_used and not need_at else 14
            if len(tweet_text_filter.replace(' ', '')) < min_letters:
                last_err = {"result": "error", "reason": Reasons.TOO_SHORT_NO_AT}
                # too short and there is no at
                continue

            possibe_search_text = []
            search_text_s = tweet_text_filter.split()

            if len(search_text_s) < 45:
                possibe_search_text.append(tweet_text_filter)

            slice_i = 2 if bool(at_to_be_used) and not need_at else 1.8
            min_word_i = 3 if bool(at_to_be_used) and not need_at else 4
            strs = []
            if len(search_text_s) >= min_word_i:
                n_1 = ceil(len(search_text_s) / slice_i)
                z_len_s = 100
                while z_len_s > min_word_i:
                    strs += [' '.join(search_text_s[i:i + n_1]) for i in range(0, len(search_text_s), n_1)]
                    z_len_s = len(strs[-2].split())
                    n_1 -= 1
                strs = set(strs)
                strs = list(filter(lambda str_: len(str_.replace(' ', '')) >= min_letters
                                                and min_word_i <= len(str_.split()) <= 45, strs))
                strs.sort(key=lambda x: len(x.split()), reverse=True)

            possibe_search_text += strs

            tweet_search_models.append(
                _TweetSearchModel(possible_at=at_to_be_used, possibe_search_text=possibe_search_text, no_at_variaton=False))
            if not need_at and at_to_be_used and 45 > len(search_text_s) > 5:
                tweet_search_models.append(
                    _TweetSearchModel(possibe_search_text=[tweet_block.tweet_text_box], no_at_variaton=True))

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models}
        elif last_err is not None:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}
