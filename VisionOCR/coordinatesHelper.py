"""
@author: rmreza

submodule from lsgapp to fixing the bounding box from googlevisionapi OCR
so we can get text per lines

as seen on :
https://github.com/sshniro/line-segmentation-algorithm-to-gcp-vision/
converted into Python and doing some modification due to some error produced
"""

from copy import deepcopy

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def fillMissingValues(data):
    """
    function to fill missing values of a point
    parsing data from OCR
    return data that filled
    """
    for item in data["textAnnotations"]:
        vertices = item["boundingPoly"]["vertices"]
        for vertex in vertices:
            if "x" not in vertex:
                vertex["x"] = 0
            if "y" not in vertex:
                vertex["y"] = 0
        # if not any("x" in x for x in v):
        #     v.append({"x" : 0})
        # if not any("x" in x for x in vertices):
        #     vertices.append({"x" : 0})
    return data


def invertAxis(data, yMax):
    """
    function to inverting axis Y, to swapping the order
    - parsing data from OCR
    - parsing yMax as maximum Y value
    return data that inverted
    """
    data = fillMissingValues(data)
    for item in data["textAnnotations"]:
        vertices = item["boundingPoly"]["vertices"]
        yArray = []
        for index in range(0, 4):
            vertices[index]['y'] = (yMax - vertices[index]['y'])
    return data


def getYMax(data):
    """
    function to get max Y axis from a 4 points
    - parsing data from OCR
    return max Y data
    """
    data = fillMissingValues(data)
    v = data["textAnnotations"][0]["boundingPoly"]["vertices"]
    yArray = []
    for i in range(0, 4):
        # print(v[i]['y'])
        yArray.append(v[i]['y'])

    return max(yArray)


def getRectangle(v, isRoundValues, avgHeight, isAdd):
    """
    function to get rectangle from each character
    - parsing v as a vertex of each character
    - parsing isRoundValues as a flag to check a round number or not
    - parsing avgHeight to use as the gradient of the character
    - parsing isAdd as a flag to add or substract the vertex
      to get min max of average point of vertex
    return json data consist of xMin, xMax, yMin, yMax
    """
    if isAdd:
        v[1]["y"] = v[1]["y"] + avgHeight
        v[0]["y"] = v[0]["y"] + avgHeight
    else:
        v[1]["y"] = v[1]["y"] - avgHeight
        v[0]["y"] = v[0]["y"] - avgHeight

    yDiff = (v[1]["y"] - v[0]["y"])
    xDiff = (v[1]["x"] - v[0]["x"])

    if xDiff != 0:
        gradient = yDiff / xDiff
    else:
        gradient = 0

    xThreshMin = 1
    xThreshMax = 8000

    if gradient == 0:
        yMin = v[0]["y"]
        yMax = v[0]["y"]
    else:
        yMin = (v[0]["y"]) - (gradient * (v[0]["x"] - xThreshMin))
        yMax = (v[0]["y"]) + (gradient * (xThreshMax - v[0]["x"]))

    if isRoundValues:
        yMin = round(yMin)
        yMax = round(yMax)

    return {"xMin": xThreshMin, "xMax": xThreshMax, "yMin": yMin, "yMax": yMax}


def createRectCoordinates(line1, line2):
    """
    function to create rectangle from each words in an overlapping vertices
    - parsing line1 as top line of rectangle
    - parsing line2 as bot line of rectangle
    return json data consist line1 and line2 xMin,xMax,yMin,yMax
    """

    return [
        [line1["xMin"], line1["yMin"]],
        [line1["xMax"], line1["yMax"]],
        [line2["xMax"], line2["yMax"]],
        [line2["xMin"], line2["yMin"]]
    ]


def getBoundingPolygon(mergedArray):
    """
    function to get the bounding polygon
    - parsing mergedArray as coordinate per words
    modified mergedArray as returned values
    """

    for i, item in enumerate(mergedArray):
        arr = []
        # print(item["description"])
        h1 = item["boundingPoly"]["vertices"][0]["y"] - \
            item["boundingPoly"]["vertices"][3]["y"]
        h2 = item["boundingPoly"]["vertices"][1]["y"] - \
            item["boundingPoly"]["vertices"][2]["y"]
        if h2 > h1:
            h = h2
        else:
            h = h1

        # threshold
        avgHeight = h * 0.3
        arr.append(item["boundingPoly"]["vertices"][1])
        arr.append(item["boundingPoly"]["vertices"][0])
        line1 = getRectangle(deepcopy(arr), True, avgHeight, True)
        arr = []
        arr.append(item["boundingPoly"]["vertices"][2])
        arr.append(item["boundingPoly"]["vertices"][3])
        line2 = getRectangle(deepcopy(arr), True, avgHeight, False)

        item['bigbb'] = createRectCoordinates(line1, line2)
        item['lineNum'] = i
        item['match'] = []
        item['matched'] = False


def combineBoundingPolygon(mergedArray):
    """
    function to combine some bounding polygon
    - parsing mergedArray to read thefour points vertices
    create the bounding polygon that check for overlapping Polygon
    then combine the overlapping polygon into 1 polygon
    modified mergedArray as returned values
    """
    for i in range(0, len(mergedArray)):
        # print("\n")
        # print("nameessss ",i)
        # print(mergedArray[i]['description'])
        # print("=====")
        bigBB = mergedArray[i]['bigbb']
        bigBB = Polygon(bigBB)

        # iterate through all the array to find the match
        for k in range(i, len(mergedArray)):
            # Do not compare with the own bounding box and which was not
            # matched with a line
            if(k != i and not mergedArray[k]['matched']):
                insideCount = 0
                for j in range(0, 4):
                    coordinate = mergedArray[k]["boundingPoly"]["vertices"][j]
                    point = Point(coordinate["x"], coordinate["y"])
                    if bigBB.contains(point):
                        insideCount = insideCount + 1

                # all four point were inside the big bb
                # print("desc {} and the count inside {}".format(
                # mergedArray[k],insideCount))
                if insideCount == 4:
                    match = {"matchCount": insideCount, "matchLineNum": k}
                    mergedArray[i]['match'].append(match)
                    mergedArray[k]['matched'] = True


def minmax(mergedArray):
    # mergedArray2 = deepcopy()
    for item in mergedArray:
        # print(item)

        minpointx = min([point['x']
                         for point in item["boundingPoly"]["vertices"]])
        maxpointy = max([point['y']
                         for point in item["boundingPoly"]["vertices"]])

        item["boundingPoly"]["minmax"] = (minpointx, maxpointy)
        # print(item["boundingPoly"]["vertices"][0])
        # print(item["boundingPoly"]["vertices"][1])
        # print(item["boundingPoly"]["vertices"][2])
        # print(item["boundingPoly"]["vertices"][3])

        # print(minpointx)
        # print(maxpointy)
        # # i = i + 1
        # if i == 20:


def traverseBoundingPolygon(mergedArray):
    """
    function to combine some bounding polygon
    - parsing mergedArray to read thefour points vertices
    create the bounding polygon that check for overlapping Polygon
    then combine the overlapping polygon into 1 polygon
    modified mergedArray as returned values
    """
    temp_mergedArray = deepcopy(mergedArray)
    for i, item in enumerate(mergedArray):
        # print(i , ": ", item['description'])
        tempelem = traverse(item, temp_mergedArray)

        for index, ind in enumerate(tempelem):
            if ind['matchLineNum'] == i:
                inds = index
                break

        index = [ind['matchLineNum'] for ind in tempelem]
        try:
            del(tempelem[index.index(i)])
        except:
            pass
        # print("tempelem : ",tempelem)
        temp_mergedArray[i]['match'] = tempelem
    return temp_mergedArray


def traverse(elements, mergedArray):
    tempelem = []
    dicttemp = {}
    # if elements['lineNum'] == 10 or
    # elements['lineNum'] == 54 or
    # elements['lineNum'] == 71:
    #     print("\n")
    #     print("desc : ",elements['description'])
    #     print("match : ",elements['match'])
    #     print("len match : ",len(elements['match']))
    #     print("\n")

    dicttemp['matchCount'] = 4
    dicttemp['matchLineNum'] = elements['lineNum']

    if len(elements['match']) > 0:
        # print("inside match")
        # print(elements['description'])
        tempelem.append(dicttemp)
        for item in elements['match']:
            tempelem.extend(
                traverse(mergedArray[item['matchLineNum']], mergedArray))
        # print("inside recur : ",tempelem)
    else:
        # print("inside not match")
        tempelem.append(dicttemp)
        # print("outside recur : ",tempelem)

    return tempelem
