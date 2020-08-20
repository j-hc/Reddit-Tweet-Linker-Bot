import base64
import json
import requests
from info import vision_api_key


class OCR:
    @staticmethod
    def vision_ocr(picurl):
        params = {"key": vision_api_key, "fields": "responses.fullTextAnnotation.text"}
        while True:
            try:
                img_bytes = requests.get(picurl).content
                break
            except:
                pass
        bss = base64.b64encode(img_bytes)
        data = json.dumps({"requests": [{"image": {"content": bss.decode()}, "features": [{"type": "TEXT_DETECTION"}]}]})
        # data = json.dumps({"requests": [{"image": {"source": {"image_uri": picurl}}, "features": [{"type": "TEXT_DETECTION"}]}]})
        response = requests.post("https://vision.googleapis.com/v1/images:annotate", data=data, params=params).json()
        if bool(response['responses'][0]):
            txt = response['responses'][0]["fullTextAnnotation"]["text"]
        else:
            txt = None
        return txt
