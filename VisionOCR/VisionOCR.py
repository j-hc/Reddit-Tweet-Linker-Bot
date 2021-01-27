import requests
import json
import base64
from info import vision_ocr_api_key


class VisionOCR:
    @staticmethod
    def _get_img_b64_from_url(url):
        img_content = requests.get(url).content
        return base64.b64encode(img_content).decode()

    @staticmethod
    def get_ocr(picuri, raw_response=True):
        image_uri_used = False
        if picuri.startswith('https'):
            image_data = {"source": {"image_uri": picuri}}
            image_uri_used = True
        else:
            with open(picuri, 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            image_data = {"content": encoded_string}

        params = {"key": vision_ocr_api_key}
        data = json.dumps({"requests": [{"image": image_data, "features": [{"type": "TEXT_DETECTION"}]}]})
        for _ in range(2):
            response = requests.post("https://vision.googleapis.com/v1/images:annotate", data=data, params=params)
            responses_zero = response.json()['responses'][0]
            if responses_zero.get('textAnnotations') is None:
                if responses_zero.get('error', {}).get('code') == 14 and image_uri_used:
                    img_b64 = VisionOCR._get_img_b64_from_url(picuri)
                    data = json.dumps({"requests": [{"image": {"content": img_b64}, "features": [{"type": "TEXT_DETECTION"}]}]})
                continue

            if raw_response:
                return responses_zero
            else:
                return responses_zero['textAnnotations'][0]['description']
        return None

    # @staticmethod
    # def _extrc_pgs(full_text_annotation):
    #     blocks = full_text_annotation['pages'][0]['blocks']
    #
    #     blocks_list = []
    #     for block in blocks:
    #         words = block['paragraphs'][0]['words']
    #         sentence = ""
    #         for word in words:
    #             symbols = word['symbols']
    #             word_text = ""
    #             for symbol in symbols:
    #                 word_text += symbol['text']
    #             sentence += word_text + ' '
    #         paragraphs_text = sentence.strip() + '\n'
    #         blocks_list.append(paragraphs_text.strip())
    #
    #     return blocks_list
