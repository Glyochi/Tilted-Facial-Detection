from unittest.case import skip
import cv2 as cv
from Point import Point
from DetectedArea import DetectedArea
from helperFunctions import *
import numpy as np


""" 
    At this point in development, what I need the ImageManager to do is store the image, perform eyes detection on the image in 0, 90, 180, and 270 degree.
    
    Then ImageManager collects all "detected eyes" called DetectedArea objs, which still has the x, y cordinate corresponding to the rotated angle of the image when
    they were found. It then proceed to convert the x, y value to the cordinate in the original non-rotated image.
    
    After that, it checks for overlapping DetectedAreas and merge them into one big DetectedArea obj.

    Once that's done, we get an array of all the location of the eyes and their sizes. We can then connect every possible pair of approximately-same-size-eyes to see 
    if the distance between them are "reasonable". If a pair of eyes has a reasonable distance inbetweeen and the size of the eyes don't differ too much, 
    we can call it a potential face.

    Once we get an array of potential faces, we rotate the image by an angle decided by the position of the two eyes (to increase precision), crop out the face (to increase performance), 
    and run facial detection on that.

    At the end, ImageManger should have an array list of all detected faces.

"""


class ImageManager:
    """
    A manager that stores the actual image and can do image processing function on it. This object will be used to take care of facial detection.
    """
    haarcascade_eye = cv.CascadeClassifier("classifier/haarcascade_eye.xml")
    haarcascade_face = cv.CascadeClassifier("classifier/haarcascade_frontalface_default.xml")
    haarcascade_nose = cv.CascadeClassifier("classifier/haarcascade_nose.xml")
    similarSizeScale = 0.5
    pairOfEyesDistanceRange = (1.5, 3.5)

    def __init__(self, img):
        """
        Constructing an ImageManger object
            :param img: the image/frame that we will run facial detection on
        """
        # Blank canvas that we are going to use to store the rotated image
        self.image = img
        self.grayImage = cv.cvtColor(self.image, cv.COLOR_BGR2GRAY)
        self.imageCenter = Point(img.shape[1]/2, img.shape[0]/2)
        self.eyes = []
        self.pairOfEyes = []
        self.faces = []
    
    

    def HELPER_runHaarDetection(self, detector, scaleFactor, minNeighbors):
        """
        Call the runHaarDetectionAngle function with 0, 90, 180, and 270 degree as angle inputs to generate a 4-tuple that
        contains 4 arrays of translated DectectedArea objects with corresponding angles.
            :param detector: the haarcascade object that is going to scan the image
            :param scaleFactor: scaleFactor parameter for detectMultiScale function
            :param minNeighbors: minNeighbors parameter for detectMultiScale function
            :return a 4-tuple of 4 arrays containing all the translated coordinates of the detected objects in the image.
        """
        AllObjects = []        

        # finding objects in 90, 180, and 270 degree rotated image
        for angle in [0, 45, 90, -45]:
            (detected, rotatedCenter) = self.HELPER_runHaarDetectionCounterClockwiseAngle(detector, angle, scaleFactor = scaleFactor, minNeighbors = minNeighbors)
            self.HELPER_rotateDetectedAreaClockwise(detected, rotatedCenter, angle)
            self.HELPER_projectDetectedArea(detected, rotatedCenter)
            AllObjects.append(detected)

        return AllObjects    


    
    def HELPER_runHaarDetectionCounterClockwiseAngle(self, detector, angle, scaleFactor, minNeighbors):
        """
        Run the given haarDetection on the image rotated by the given angle and generate 1 array that 
        contain detected objects found.         
            :param detector: the haarcascade object that is going to scan the image
            :param angle: the angle by which the image is rotated
            :param scaleFactor: scaleFactor parameter for detectMultiScale function
            :param minNeighbors: minNeighbors parameter for detectMultiScale function
            :return a 2-tuple with the first element being an array containing all the raw coordinates of the detected objects in the rotated image,
            and the second element the Point object containing the coordinates of the center of the rotated image.
        """

        angle = angle % 360

        # finding objects in then given angle degree rotated image
       
        rotatedGrayImage = rotateCounterClockwise(self.grayImage, angle)
            
        # Collecting raw detected objects received from detectMultiScale
        rawObjs = detector.detectMultiScale(rotatedGrayImage, scaleFactor = scaleFactor, minNeighbors = minNeighbors)
            
        detectedAreas = []
        rotatedCenter = Point(rotatedGrayImage.shape[1]/2, rotatedGrayImage.shape[0]/2)

        for obj in rawObjs:
            # Convert raw information into DetectedArea obj
            area = DetectedArea((obj[0], obj[1]), (obj[2], obj[3]))

            # Put the translated DetectedArea into translatedObj array
            detectedAreas.append(area)

        return (detectedAreas, rotatedCenter)    


    def HELPER_rotateDetectedAreaClockwise(self, rawPositions, origin, angle):
        """
        Rotate detectedAreas in rawPositions around the given origin
            :param rawPositions: the array that contains detectedAreas with raw values taken from detectMultiScale
            :param origin: the origin which the detectedAreas are rotating around
            :param angle: the angle by which the image was rotated when detectMultiScale ran
            :return an array containing detectedAreas with translated coordinates in the non-rotated image
        """
        angle = angle % 360
        if angle == 0:
            return rawPositions

        # Translate the coordinates to the coordinates in the non-rotated image
        for area in rawPositions:
            area.rotateAreaClockwise(origin, angle)

        return rawPositions


    def HELPER_projectDetectedArea(self, rawPositions, rotatedCenter):
        """
        Project the raw positions such that the new positions relative to self.imageCenter is the same
        as relative positions of the old Coordinates to rotatedCenter.
            :param rawPositions: the array that contains detectedAreas
            :return an array containing detectedAreas with projected coordinates
        """
        # Translate the coordinates to the coordinates in the non-rotated image
        for area in rawPositions:
            area.projectArea(rotatedCenter, self.imageCenter)

        return rawPositions


        

    def HELPER_mergeDetectedObjs(self, tuple):
        """
        Given a four-tuple containing 4 arrays of detected objects, scan through all of them and if find two duplicates (similar detected objects with similar 
        sizes and positions), merge them and put all the unique detected object in an array. 
            :return an array that contains all the unique detected objects.
        """
        array0 = tuple[0]
        others = []
        for i in range(1,len(tuple)):
            others.append(tuple[i])


        for i in range(len(array0) - 1):
            for j in range(i + 1, len(array0)):
                if array0[i].similarSize(array0[j], self.similarSizeScale) and array0[i].overlap(array0[j]):
                        array0[i].merge(array0[j])
                        array0.pop(j)
                        j = j - 1

        for array in others:
            for area in array:
                matched = False
                # Scan through the array to find matches
                for area0 in array0:
                    if area0.similarSize(area, self.similarSizeScale) and area0.overlap(area):
                        area0.merge(area)
                        matched = True
                        break
                
                # if didnt find any matches then append it onto array0
                if matched == False:
                    array0.append(area)    
        
        return array0



    def findPairsOfEyes(self, scaleFactor, minNeighbors):
        """
        Find the pairs of eyes in the image after applying haarcascade eye detection on the 0, 90, 180, and 270 degree rotated image.
            :return array of pairs of eyes
        """
        
        eyes = self.HELPER_mergeDetectedObjs(self.HELPER_runHaarDetection(self.haarcascade_eye, scaleFactor, minNeighbors))

        pairOfEyes = []
        
        for i in range(len(eyes) - 1):
            for j in range(i,len(eyes)):
                if eyes[i].similarSize(eyes[j], self.similarSizeScale):
                    dist = eyes[i].center.distTo(eyes[j].center)
                    averageRadius = (eyes[1].radius + eyes[j].radius)/2
                    if dist < self.pairOfEyesDistanceRange[1] * averageRadius and dist > self.pairOfEyesDistanceRange[0] * averageRadius:
                        # Let the left most eye be the first eye. This is for calculating relative angle of the face in findFacesUsingPairOfEyes method
                        if eyes[i].center.x < eyes[j].center.x:
                            pairOfEyes.append((eyes[i], eyes[j]))
                        else:
                            pairOfEyes.append((eyes[j], eyes[i]))

        return pairOfEyes

 
    def DEBUG_findFacesUsingPairOfEyes(self, pairOfEyes, scaleFactor, minNeighbors):
        """
        Using given pairs of eyes, for each pair find the angle the face is leaning, crop the area the face could be out and run haarDetection on that area.
        Return an array of all detectedAreas encapsulating faces.
            :param pairOfEyes: 2-tuple (left eye, right eye)
            :param scaleFactor: parameter for detectMultiScale
            :param minNeighbors: parameter for detectedMultiScale
            return array of all detected faces
        """

        # For right now, let face width be 6 average radius, and height be 10 average radius with 5 average radiuses from 2 eyes center to the top 
        # 5 average radiuses from 2 eyes center to the chin

        debugArrayFaces = []
        debugPotentialFaceNumber = 1
        for pair in pairOfEyes:
            
            leftEye = pair[0]
            rightEye = pair[1]
            eyeAverageRadius = (leftEye.radius + rightEye.radius)/2
            # halfFaceDimensions store the distance from faceOrigin to the left border, to the upper border, and to the lower border
            # faceMinRadius is the min radius of the rectangle encapsulating the detected Face
            halfFaceDimensions = (eyeAverageRadius * 4, eyeAverageRadius * 5, eyeAverageRadius * 5)
            faceMinRadius = eyeAverageRadius * 3

            # relative angle range from 270 -> 0 -> 90 degree because faces usually aren't up side down, still this function takes care of that case also
            relativeAngle = (leftEye.center.relativeAngle(rightEye.center) + 90) % 180 - 90
            originalImageCenter = Point(self.grayImage.shape[1]/2, self.grayImage.shape[0]/2)
            faceOrigin = Point((leftEye.center.x + rightEye.center.x)/2,(leftEye.center.y + rightEye.center.y)/2)
           
            # Rotate the face origin point and the image such that the face is straightened up
            rotatedGrayImage = rotateClockwise(self.grayImage, relativeAngle)
            rotatedImageCenter = Point(rotatedGrayImage.shape[1]/2, rotatedGrayImage.shape[0]/2)
            rotatedFaceOrigin = faceOrigin.rotatePointClockwise(originalImageCenter, relativeAngle)
            rotatedFaceOrigin = rotatedFaceOrigin.projectPoint(originalImageCenter, rotatedImageCenter)
            
            
            
            # DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- 
            debugOriginalImage = rotateClockwise(self.image, 0)
            leftEye.draw(debugOriginalImage, (255,0,255), 2)
            rightEye.draw(debugOriginalImage, (0,255,255), 2)
            cv.circle(debugOriginalImage, faceOrigin.exportCoordinates(), 0, (0, 255, 0), 20)
            debugRotatedOriginalImage = rotateClockwise(debugOriginalImage, relativeAngle)
            cv.circle(debugRotatedOriginalImage, rotatedFaceOrigin.exportCoordinates(), 0, (255, 255, 255), 12)
            # DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- DEBUG step --- 
            


            # Crop the potential face out
            cropRangeMinY = int(max(0, rotatedFaceOrigin.y - halfFaceDimensions[1]))
            cropRangeMaxY = int(min(rotatedGrayImage.shape[0], rotatedFaceOrigin.y + halfFaceDimensions[2]))

            cropRangeMinX = int(max(0, rotatedFaceOrigin.x - halfFaceDimensions[0]))
            cropRangeMaxX = int(min(rotatedGrayImage.shape[1], rotatedFaceOrigin.x + halfFaceDimensions[0]))

            try:
                rotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX), dtype='uint8')
                rotatedCrop[0: rotatedCrop.shape[0], 0: rotatedCrop.shape[1]] = \
                    rotatedGrayImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]
             
            except:
                rotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX, 3), dtype ='uint8')
                rotatedCrop[0: rotatedCrop.shape[0], 0: rotatedCrop.shape[1]] = \
                    rotatedGrayImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]
   
            try:
                debugRotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX), dtype ='uint8')
                debugRotatedCrop[0: debugRotatedCrop.shape[0], 0: debugRotatedCrop.shape[1]] = debugRotatedOriginalImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]
            except:
                debugRotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX, 3), dtype ='uint8')
                debugRotatedCrop[0: debugRotatedCrop.shape[0], 0: debugRotatedCrop.shape[1]] = debugRotatedOriginalImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]

        
            rotatedFaceCenter = Point((cropRangeMinX + cropRangeMaxX)/2, (cropRangeMinY + cropRangeMaxY)/2)
            croppedCenter = Point(rotatedCrop.shape[1]/2, rotatedCrop.shape[0]/2)


            # find the face in the cropped Area
            detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)


            # DEBUGING AREA
            debugRotatedCrop = cv.circle(debugRotatedCrop, croppedCenter.exportCoordinates(), 0, (255, 255, 255), 6)

            # DEBUGING AREA


            boolUpSideDown = False

            if len(detectedFaces) == 0:
                # Scan the image upside down in case of upside down faces
                rotatedCrop = rotateClockwise(rotatedCrop, 180)
                detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)
                if len(detectedFaces) == 0:
                    continue
                boolUpSideDown = True


            # merge smaller faces to the biggest face
            biggestFace = detectedFaces[0]
            for i in range(1, len(detectedFaces)):
                # Doesn't have to be too complicated, if one dimension is larger the other is 99% of the time larger as well
                if detectedFaces[i][2] > biggestFace[2]:
                    biggestFace = detectedFaces[i]


            # if face's radius is too small then its not a face (face right now is a 4-tuple (x, y, w, h))
            if biggestFace[2] ** 2 + biggestFace[3] ** 2 < (faceMinRadius * 2) ** 2:

                if boolUpSideDown:
                    continue

                # Scan the image upside down in case of upside down faces
                rotatedCrop = rotateClockwise(rotatedCrop, 180)
                detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)
                if len(detectedFaces) == 0:
                    continue
                boolUpSideDown = True

                
                # merge smaller faces to the biggest face
                biggestFace = detectedFaces[0]
                for i in range(1, len(detectedFaces)):
                    # if one dimension is larger the other is 99% of the time larger as well
                    if detectedFaces[i][2] > biggestFace[2]:
                        biggestFace = detectedFaces[i]

                if biggestFace[2] ** 2 + biggestFace[3] ** 2 < (faceMinRadius * 2) ** 2:
                    continue


            biggestFace = DetectedArea((biggestFace[0],biggestFace[1]), (biggestFace[2], biggestFace[3]))

            
            if boolUpSideDown:
                biggestFace.rotateAreaClockwise(croppedCenter, 180)

            # Convert biggestFace coordinates from being in the cropped image to the original image
            biggestFace.draw(debugRotatedCrop, (0, 0, 255), 2)
            cv.imshow("Potential face " + str(debugPotentialFaceNumber), resizeMinTo(debugRotatedCrop, 250))

            debugArrayFaces.append((biggestFace.copy(), rotatedFaceCenter, croppedCenter, rotatedImageCenter, relativeAngle, originalImageCenter)) 
                
            
            debugPotentialFaceNumber = debugPotentialFaceNumber + 1


        return debugArrayFaces


    def findFacesUsingPairOfEyes(self, pairOfEyes, scaleFactor, minNeighbors):
        """
        Using given pairs of eyes, for each pair of similar-size eyes, find the angle the face is leaning, crop the area the face could be out and run haarDetection on that area.
        Return an array of all detectedAreas encapsulating faces.
            :param pairOfEyes: 2-tuple (left eye, right eye)
            :param scaleFactor: parameter for detectMultiScale
            :param minNeighbors: parameter for detectedMultiScale
            return array of all detected faces
        """

        faces = [] 

        # For right now, let face width be 6 average radius, and height be 10 average radius with 5 average radiuses from 2 eyes center to the top 
        # 5 average radiuses from 2 eyes center to the chin. I'm going to make the height ratio 3 top:5 bottom once i added mouth/nose detection for orientation
        
        for pair in pairOfEyes:
            
            leftEye = pair[0]
            rightEye = pair[1]
            eyeAverageRadius = (leftEye.radius + rightEye.radius)/2
            # halfFaceDimensions store the distance from faceOrigin to the left border, to the upper border, and to the lower border
            # faceMinRadius is the min radius of the rectangle encapsulating the detected Face
            halfFaceDimensions = (eyeAverageRadius * 4, eyeAverageRadius * 5, eyeAverageRadius * 5)
            faceMinRadius = eyeAverageRadius * 3

            # relative angle range from 270 -> 0 -> 90 degree because faces usually aren't up side down, still this function takes care of that case also
            relativeAngle = (leftEye.center.relativeAngle(rightEye.center) + 90) % 180 - 90
            originalImageCenter = Point(self.grayImage.shape[1]/2, self.grayImage.shape[0]/2)
            faceOrigin = Point((leftEye.center.x + rightEye.center.x)/2,(leftEye.center.y + rightEye.center.y)/2)
           
            # Rotate the face origin point and the image such that the face is straightened up
            rotatedGrayImage = rotateClockwise(self.grayImage, relativeAngle)
            rotatedImageCenter = Point(rotatedGrayImage.shape[1]/2, rotatedGrayImage.shape[0]/2)
            rotatedFaceOrigin = faceOrigin.rotatePointClockwise(originalImageCenter, relativeAngle).projectPoint(originalImageCenter, rotatedImageCenter)

            # Crop the potential face out
            cropRangeMinY = int(max(0, rotatedFaceOrigin.y - halfFaceDimensions[1]))
            cropRangeMaxY = int(min(rotatedGrayImage.shape[0], rotatedFaceOrigin.y + halfFaceDimensions[2]))

            cropRangeMinX = int(max(0, rotatedFaceOrigin.x - halfFaceDimensions[0]))
            cropRangeMaxX = int(min(rotatedGrayImage.shape[1], rotatedFaceOrigin.x + halfFaceDimensions[0]))

            try:
                rotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX), dtype='uint8')
                rotatedCrop[0: rotatedCrop.shape[0], 0: rotatedCrop.shape[1]] = \
                    rotatedGrayImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]
             
            except:
                rotatedCrop = np.zeros((cropRangeMaxY - cropRangeMinY, cropRangeMaxX - cropRangeMinX, 3), dtype ='uint8')
                rotatedCrop[0: rotatedCrop.shape[0], 0: rotatedCrop.shape[1]] = \
                    rotatedGrayImage[cropRangeMinY:cropRangeMaxY, cropRangeMinX:cropRangeMaxX]
        
            rotatedFaceCenter = Point((cropRangeMinX + cropRangeMaxX)/2, (cropRangeMinY + cropRangeMaxY)/2)
            croppedCenter = Point(rotatedCrop.shape[1]/2, rotatedCrop.shape[0]/2)


            # find the face in the cropped Area
            detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)
            boolUpSideDown = False


            # if found no faces right side up
            if len(detectedFaces) == 0:
                # Scan the image upside down
                rotatedCrop = rotateClockwise(rotatedCrop, 180)
                detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)
                if len(detectedFaces) == 0:
                    continue
                boolUpSideDown = True


            # merge smaller faces to the biggest face
            biggestFace = detectedFaces[0]
            for i in range(1, len(detectedFaces)):
                # Doesn't have to be too complicated, if one dimension is larger the other is 99% of the time larger as well
                if detectedFaces[i][2] > biggestFace[2]:
                    biggestFace = detectedFaces[i]


            # if face's radius is too small then its not a face (face right now is a 4-tuple (x, y, w, h))
            if biggestFace[2] ** 2 + biggestFace[3] ** 2 < (faceMinRadius * 2) ** 2:

                if boolUpSideDown:
                    continue

                # Scan the image upside down in case of upside down faces
                rotatedCrop = rotateClockwise(rotatedCrop, 180)
                detectedFaces = self.haarcascade_face.detectMultiScale(rotatedCrop, scaleFactor, minNeighbors)
                if len(detectedFaces) == 0:
                    continue
                boolUpSideDown = True

                
                # merge smaller faces to the biggest face
                biggestFace = detectedFaces[0]
                for i in range(1, len(detectedFaces)):
                    # if one dimension is larger the other is 99% of the time larger as well
                    if detectedFaces[i][2] > biggestFace[2]:
                        biggestFace = detectedFaces[i]

                # if face's radius is too small then its not a face (face right now is a 4-tuple (x, y, w, h))
                if biggestFace[2] ** 2 + biggestFace[3] ** 2 < (faceMinRadius * 2) ** 2:
                    continue

            
            biggestFace = DetectedArea((biggestFace[0],biggestFace[1]), (biggestFace[2], biggestFace[3]))
            

            if boolUpSideDown:
                biggestFace.rotateAreaClockwise(croppedCenter, 180)

            # Convert biggestFace coordinates from being in the cropped image to the original image
            biggestFace.projectArea(croppedCenter, rotatedFaceOrigin)
            biggestFace.rotateAreaCounterClockwise(rotatedImageCenter, relativeAngle)
            biggestFace.projectArea(rotatedImageCenter, originalImageCenter)

            faces.append(biggestFace)

        return faces


    def findFaces(self, scaleFactor, minNeighbors):
        """
        Find faces in the image and return them as detectedArea objects in an array
            :param scaleFactor: paramter for detectMultiScale
            :param minNeighbors: parameter for detectMultiScale
            :return an array of faces as detectedArea objects
        """
        return self.findFacesUsingPairOfEyes(self.findPairsOfEyes(scaleFactor, minNeighbors), scaleFactor, minNeighbors)

                











