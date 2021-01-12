"""
@author: rmreza

submodule from lsgapp to fixing the bounding box from googlevisionapi OCR
so we can get text per lines

as seen on :
https://github.com/sshniro/line-segmentation-algorithm-to-gcp-vision/
converted into Python and doing some modification due to some error produced
"""

from copy import deepcopy
from . import coordinatesHelper as ch


def mergeNearByWords(data):
    """
    function to merge words that closes into a one bounding box
    parsing json data from googlevisionapi
    return finalArray as text object
    """

    if not data or not data.get("textAnnotations", None):
        return None

    yMax = ch.getYMax(data)
    data = ch.invertAxis(data, yMax)

    lines = data["textAnnotations"][0]["description"].split('\n')

    rawText = deepcopy(data["textAnnotations"])

    lines.reverse()
    rawText.reverse()

    rawText.pop()
    mergedArray = getMergedLines(lines, rawText)

    ch.minmax(mergedArray)
    mergedArray = sorted(mergedArray, key=lambda x: (
        x['boundingPoly']['minmax'][0], -x['boundingPoly']['minmax'][1]))

    ch.getBoundingPolygon(mergedArray)

    ch.combineBoundingPolygon(mergedArray)
    mergedArray = ch.traverseBoundingPolygon(mergedArray)
    finalArray = constructLineWithBoundingPolygon(mergedArray)
    return finalArray


def getMergedLines(lines, rawText):
    """
    function to merge the overlapping points
    - parsing lines as a googlevisionapi OCR full result per lines
    - parsing rawText as a googlevisionapi OCR full result per lines
      basically a copy of lines, used to comparing
    return mergedArray as a list object
    """
    mergedArray = []
    while len(lines) != 1:
        l = lines.pop()
        l1 = deepcopy(l)
        status = True

        data = ""
        mergedElement = ""

        while True:
            try:
                wElement = rawText.pop()
            except:
                break

            w = wElement["description"]
            elVer = wElement["boundingPoly"]["vertices"]
            try:
                index = str(l).index(str(w))
            except:
                if status:
                    status = False
                    mergedElement = wElement

                print("failed on this character = {}".format(str(w)))

                mergedElement["description"] = l1
                mergedElement["boundingPoly"]["vertices"][1] = elVer[1]
                mergedElement["boundingPoly"]["vertices"][2] = elVer[2]
                mergedArray.append(mergedElement)
                break
            l = l[index + len(w):]
            if status:
                status = False
                mergedElement = wElement

            if l == "":
                mergedElement["description"] = l1
                mergedElement["boundingPoly"]["vertices"][1] = elVer[1]
                mergedElement["boundingPoly"]["vertices"][2] = elVer[2]
                mergedArray.append(mergedElement)
                break

    return mergedArray


def constructLineWithBoundingPolygon(mergedArray):
    """
    function to imaginary make and connect some polygon object that overlapping
    by doing line segmentation so it becomes a one bounding box
    parsing mergedArray an array of four points that build a bounding polygon
    return result as a text object
    """
    finalArray = []
    for i, item in enumerate(mergedArray):
        if not item["matched"]:
            if len(item["match"]) == 0:
                yMax = max([vertex['y']
                            for vertex in item["boundingPoly"]["vertices"]])
                finalArray.append([item["description"], yMax])
            else:
                finalArray.append(arrangeWordsInOrder(mergedArray, i))
        else:
            continue
    finalArray = sorted(finalArray, key=lambda x: x[1], reverse=True)

    result = [item[0] for item in finalArray]
    result = "\n".join(result)
    return result


def arrangeWordsInOrder(mergedArray, k):
    """
    function to arrange the words per lines based on a points
    - parsing mergedArray as data
    - parsing k as an index array
    return mergedLine as the data per line and yMax as maximum point as a base
    """

    matched = [mergedArray[k]]

    line = mergedArray[k]['match']
    temp = [mergedArray[item['matchLineNum']] for item in line]
    matched.extend(temp)
    matched = sorted(
        matched, key=lambda k: k["boundingPoly"]["vertices"][0]["x"])

    temp_mergedLine = []
    temp_max = 0
    for item in matched:
        temp_yMax = max([vertex['y']
                         for vertex in item["boundingPoly"]["vertices"]])
        if temp_yMax >= temp_max:
            temp_max = temp_yMax
        temp_mergedLine.append(item["description"])

    mergedLine = " ".join(temp_mergedLine)
    yMax = temp_max

    return [mergedLine, yMax]
