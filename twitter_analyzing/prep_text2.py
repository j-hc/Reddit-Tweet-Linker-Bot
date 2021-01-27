from .err_reasons import Reasons
from TwitterClient import TWStatus
import re
from math import ceil
from collections import namedtuple


class TextPrep:
    #  YES I KNOW THIS WHOLE THING IS UGLY ASF

    tw_username_dot = "·"
    three_dot = ".."  # … for yandex ocr # . for vision ocr

    re_replying2 = re.compile(r'Antwort an|Replying to|adlı kişiye|adlı kullanıcı(lara|ya)|yanıt olarak|svar till|ve diğer [0-9]+ kişiye|En réponse à|En respuesta a')
    re_endoftweet2 = re.compile(r'Twitter for|Translate Tweet|Tweeti Çevir|Twitter Web App|PM - |for (iOS|Android)| Translate from |\d{1,2}[/.-]\d{1,2}[/.-]\d{1,4}|'
                                r'Show this thread|dilinden Google tarafından|[0-9].*? Retweet.*?[0-9].*? Beğeni|Bu Tweet dizisini göster|Tweet etkinliğini görüntüle|'
                                r'[0-9].*? Retweets.*?[0-9].*? Likes|Show replies')
    re_twitterusername2 = re.compile(r"@([A-Za-z0-9_]{3,15})")

    re_two_space = re.compile(' +')
    re_only_letters_whitespace = re.compile('[^a-zA-Z!?ışçöğü ]')

    tweet_search_model = namedtuple("tweet_search_model", "possible_at possibe_search_text no_at_variaton")
    tweet_block = namedtuple("tweet_block", "tweeter_box tweet_text_box")

    def __init__(self, tw_client):
        self.max_word_x_diff = 0
        self.max_line_x_diff = 0
        self.max_line_y_diff = 0
        self.max_word_y_diff = 0
        self.other_chars_bottom_y_diff_plus = 0
        self.tw_client = tw_client

        self.d = False
        self.b = False

    def _print_d(self, p=''):
        if self.d:
            print(p)

    def _print_b(self, p=''):
        if self.b:
            print(p)

    def extract_text_blocks(self, ocr_data, return_raw_blocks=True):
        def _truncated_float(flt, _f='3'):
            _f_ = f'%.{_f}f'
            return float(_f_ % flt)

        self.max_word_y_diff = 15.85
        self.max_word_x_diff = 59.0
        self.max_line_x_diff = 32.5
        self.max_line_y_diff = 37.1
        self.other_chars_bottom_y_diff_plus = 6.0

        text_annotations = ocr_data['textAnnotations'][1:]
        vertice_texts = []
        id_incrementer = 0
        # total_y_diff_of_words = 0
        for text_annotation in text_annotations:
            vertices = text_annotation['boundingPoly']['vertices']
            text = text_annotation['description']
            box = []
            for vertic_i, vertice in enumerate(reversed(vertices)):
                x_val = vertice.get('x', 0)
                y_val = vertice.get('y', 0)
                if text == self.tw_username_dot and (vertic_i == 0 or vertic_i == 1):
                    y_val += self.other_chars_bottom_y_diff_plus
                elif text == self.tw_username_dot and (vertic_i == 2 or vertic_i == 3):
                    y_val -= self.other_chars_bottom_y_diff_plus

                if any(lt in text for lt in ['g', 'p', 'y', 'ğ']) and (vertic_i == 0 or vertic_i == 1):
                    y_val -= self.other_chars_bottom_y_diff_plus

                box.append((x_val, y_val))
            # total_y_diff_of_words += abs((box[0][1] + box[1][1]) - (box[2][1] + box[3][1])) / 2
            vertice_texts.append((text, tuple(box), id_incrementer))
            id_incrementer += 1

        # avg_y_diff_of_words = total_y_diff_of_words / id_incrementer
        # print(avg_y_diff_of_words)

        # latest_vertice_bottom_y = vertice_texts[-1][1][0][1]
        # first_vertice_top_y = vertice_texts[0][1][3][0]
        # y_difference = latest_vertice_bottom_y - first_vertice_top_y

        # print(f"y diff: {y_difference} max_line_y_diff: {self.max_line_y_diff}")
        # print(f"y diff: {y_difference} max_word_y_diff: {self.max_word_y_diff}")

        lines = []
        red_references = set()
        elem_id_incrementer = 0
        for vertice_text_base in vertice_texts:
            if vertice_text_base[2] in red_references:
                continue
            red_references.add(vertice_text_base[2])

            nearyby_y_vals = [vertice_text_base]
            self._print_d(f"base: {vertice_text_base}")
            for vertice_text in vertice_texts:
                if vertice_text[2] in red_references:
                    continue

                box = vertice_text[1]
                last_elem_box_of_line = nearyby_y_vals[-1][1]

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
                self._print_d(f"ref: {vertice_text}")
                self._print_d(f"last elem {nearyby_y_vals[-1]}")
                self._print_d(f"x check: {avg_left_x_val_of_last_elem} - {avg_right_x_val_of_ref}")
                self._print_d(f"y check: {avg_bottom_y_val_of_last_elem} - {avg_bottom_y_val_ref}")
                self._print_d(f"y {check_y_diff}<{self.max_word_y_diff} : x {check_x_diff} < {self.max_word_x_diff}")
                if check_y_diff < self.max_word_y_diff and check_x_diff < self.max_word_x_diff:
                    self._print_d("eklendi")
                    self._print_d()
                    nearyby_y_vals.append(vertice_text)
                    red_references.add(vertice_text[2])
                    nearyby_y_vals.sort(key=lambda x: x[1][0][0])
            self._print_d()

            nearyby_y_vals_len = len(nearyby_y_vals)

            total_bottom_y = 0
            for box_y in nearyby_y_vals:
                total_bottom_y += (box_y[1][0][1] + box_y[1][1][1]) / 2.0
            avg_bottom_y_of_line = _truncated_float(total_bottom_y / nearyby_y_vals_len)

            total_top_y = 0
            for box_y in nearyby_y_vals:
                total_top_y += (box_y[1][2][1] + box_y[1][3][1]) / 2.0
            avg_top_y_of_line = _truncated_float(total_top_y / nearyby_y_vals_len)

            avg_left_x_of_line = _truncated_float((nearyby_y_vals[0][1][0][0] + nearyby_y_vals[0][1][3][0]) / 2.0)
            # avg_bottom_y_of_line = _truncated_float(sum([(box_y[1][0][1] + box_y[1][1][1]) / 2.0 for box_y in nearyby_y_vals]) / nearyby_y_vals_len)
            # avg_top_y_of_line = _truncated_float(sum([(box_y[1][2][1] + box_y[1][3][1]) / 2.0 for box_y in nearyby_y_vals]) / nearyby_y_vals_len)

            line_box = (avg_left_x_of_line, avg_bottom_y_of_line, avg_top_y_of_line)
            line_text = ' '.join([str(txt[0]) for txt in nearyby_y_vals])
            lines.append((line_text, line_box, elem_id_incrementer))
            elem_id_incrementer += 1

        lines.sort(key=lambda x: x[1][1])
        # for l in lines:
        #     print(l)
        # exit()
        blocks = []
        red_references = set()
        for line_base in lines:
            if line_base[2] in red_references:
                continue
            red_references.add(line_base[2])
            box_base = line_base[1]
            avg_left_x_of_line_base = box_base[0]
            same_parag_lines = [line_base[:2]]

            self._print_b(f"base: {line_base}")
            for line in lines:
                if line[2] in red_references:
                    continue
                box = line[1]
                line_last_elem = same_parag_lines[-1]

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
                self._print_b(f"{ref_elem_y_of_top} - {last_elem_y_of_bottom}")
                self._print_b(f"{bottom_top_min_diff} < {self.max_line_y_diff} : {check_left_x_diff}<{self.max_line_x_diff}")
                if check_left_x_diff < self.max_line_x_diff and bottom_top_min_diff < self.max_line_y_diff:
                    red_references.add(line[2])
                    same_parag_lines.append(line[:2])
                    self._print_b("eklendi")
                    self._print_b()
                    same_parag_lines.sort(key=lambda x: x[1][1])
            self._print_b()
            top_y_of_parag = same_parag_lines[0][1][2]
            bottom_y_of_parag = same_parag_lines[-1][1][1]
            avg_left_x_of_parag = float(sum([box_x[1][0] for box_x in same_parag_lines]) / len(same_parag_lines))
            parag_box = (avg_left_x_of_parag, bottom_y_of_parag, top_y_of_parag)
            blocks.append((tuple(same_parag_lines), parag_box))
        blocks.sort(key=lambda x: x[1][1])
        # for b in blocks:
        #     print(b)
        # exit()
        if return_raw_blocks:
            return blocks
        else:
            return ['\n'.join([txt[0] for txt in x]) for x in [blc[0] for blc in blocks]]

    def create_tweet_blocks(self, text_blocks):
        append_trailing_lines = False
        tweet_blocks = []
        tweet_text = []
        last_ending = True
        tweeter_box = None
        last_line_left_x = None
        added_block_indexes = set()
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

                if tweeter_box is not None and abs(tweeter_bottom_y - current_bottom_y) < self.max_word_y_diff:
                    # print(f"is same line {line_text} | {tweeter_bottom_y}-{current_bottom_y}={abs(tweeter_bottom_y - current_bottom_y)}<{self.max_word_y_diff}")
                    continue

                if bool(self.re_replying2.search(line_text)) or line_text == 'olarak':
                    # print(f"line_text replying {line_text}")
                    tweet_text = []
                    if not append_trailing_lines:
                        tweeter_box = None
                        append_trailing_lines = True
                    continue

                ending = True if bool(self.re_endoftweet2.search(line_text)) else False
                if append_trailing_lines:
                    if not ending:
                        if not len(self.re_only_letters_whitespace.sub('', line_text)) <= 4:
                            # print(f"eklendi: {line_text}")
                            tweet_text.append(line_text)
                        elif line_index != lines_last_index:
                            # print(f"skipped2: {line_text} {self.re_only_letters_whitespace.sub('', line_text)}")
                            continue
                        else:
                            # print(f"skipped3: {line_text} {self.re_only_letters_whitespace.sub('', line_text)}")
                            pass
                    if line_index == lines_last_index or ending:
                        if bool(tweet_text):
                            tweet_block2append = self.tweet_block(tweeter_box=tweeter_box, tweet_text_box=' '.join(tweet_text))
                            if block_i not in added_block_indexes:
                                tweet_blocks.append(tweet_block2append)
                                # print(tweet_block2append)
                                # print()
                                added_block_indexes.add(block_i)
                        tweet_text = []
                        append_trailing_lines = False
                        break
                elif line_text.count('@') == 1 or (self.tw_username_dot in line_text and not ending and len(line_text.split(self.tw_username_dot)[0]) >= 0):
                    tweeter_box = None
                    try:
                        tweeter_line_text = line_text.split('@')[1].split()[0]
                    except:
                        tweeter_line_text = line_text
                    if self.three_dot not in tweeter_line_text:
                        tweeter_box_try = self.re_twitterusername2.search(line_text)
                        if bool(tweeter_box_try):
                            tweeter_box = tweeter_box_try.group(1)
                    tweeter_bottom_y = line_box[1]
                    # print(f"found: {line_text}")
                    # print()
                    append_trailing_lines = True
                elif ending and not last_ending and last_line_left_x is not None and abs(current_line_left_x - last_line_left_x) < self.max_line_x_diff:
                    block_index_to_extract_text_from = block_i - 1
                    if line_index != 0 and block_i not in added_block_indexes:
                        # print(f"ending l: {line_text}")
                        lines_of_possible_tweet = lines_it[:line_index]
                        lines_text_only = ' '.join([li[0] for li in lines_of_possible_tweet
                                                    if self.re_endoftweet2.search(li[0]) is None and self.re_replying2.search(li[0]) is None])
                        tweet_block2append = self.tweet_block(tweeter_box=None, tweet_text_box=lines_text_only)
                        tweet_blocks.append(tweet_block2append)
                        added_block_indexes.add(block_i)
                    elif block_i != 0 and block_index_to_extract_text_from not in added_block_indexes:
                        # print(f"ending b: {line_text}")
                        lines_of_possible_tweet = text_blocks[block_index_to_extract_text_from][0]
                        lines_text_only = ' '.join([li[0] for li in lines_of_possible_tweet
                                                    if self.re_endoftweet2.search(li[0]) is None and self.re_replying2.search(li[0]) is None])
                        tweet_block2append = self.tweet_block(tweeter_box=None, tweet_text_box=lines_text_only)
                        tweet_blocks.append(tweet_block2append)
                        added_block_indexes.add(block_index_to_extract_text_from)
                last_ending = ending
                last_line_left_x = current_line_left_x
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

            search_list = tweet_block.tweet_text_box.split()
            # tweet_text_filter = [x for x in tweet_block.tweet_text_box.split() if not all(likelylink in x for likelylink in ['/', '…'])]
            tweet_text_filter = filter(lambda w: not (w is None or all(x in w for x in ['.', '/'])), search_list)
            tweet_text_filter = ' '.join(tweet_text_filter)
            # tweet_text_filter = ' '.join(filter(lambda w: len(w) > 2, tweet_text_filter))
            tweet_text_filter = self.re_two_space.sub(' ', tweet_text_filter)

            if not bool(tweet_text_filter):
                # print("no text prepped")
                last_err = {"result": "error", "reason": Reasons.DEFAULT}
                continue

            min_letters = 7 if at_to_be_used and not need_at else 14
            if len(tweet_text_filter.replace(' ', '')) < min_letters:
                last_err = {"result": "error", "reason": Reasons.TOO_SHORT_NO_AT}
                # print("too short and there is no at")
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

                    # if len(strs[-1].split()) < min_word_i:
                    #     strs.pop(-1)
                    n_1 -= 1

                strs = set(strs)
                strs = list(filter(lambda str_: len(str_.replace(' ', '')) >= min_letters and len(str_.split()) >= min_word_i, strs))
                strs.sort(key=lambda x: len(x.split()), reverse=True)

            possibe_search_text += strs

            tweet_search_models.append(self.tweet_search_model(possible_at=at_to_be_used, possibe_search_text=possibe_search_text, no_at_variaton=False))
            if not need_at and at_to_be_used and 45 > len(search_text_s) > 5:
                tweet_search_models.append(self.tweet_search_model(possible_at=None, possibe_search_text=[tweet_block.tweet_text_box], no_at_variaton=True))

        if bool(tweet_search_models):
            return {"result": "success", "tweets2search": tweet_search_models}
        elif last_err is not None:
            return last_err
        else:
            return {"result": "error", "reason": Reasons.DEFAULT}
