#import necesary packages
from collections import deque #a list data structure with really fast past N locations. this draws the tail of the ball
import numpy as np
import argparse
import imutils #opencv convenience functions to make basic tasks easier (pip install imutils)
import cv2
import serial
import time
import psutil
import os
import math

#Function used to calculate the velocity to send to the arduino.
#accounts for a central "deadzone"
def calculateDistanceToMove(coord, res, maxVel):
	#vel = int(1500 + float((coord - res // 2)) / (res // 2) *  maxVel)
	normal = float((coord - res // 2)) / (res // 2)
	if normal != 0:
		normal = (normal ** 2) * abs(normal) / normal
	
	vel = int(1500 + normal * maxVel)
	return vel
	

	

def main():
	
	#construct the argument parse and then parse the arguments
	ap = argparse.ArgumentParser()
	ap.add_argument("-v", "--video", help = "path to the (optional) video file")
	ap.add_argument("-t", "--tail",  required=False, action='store_true', help = "Show a tail and the center of mass")
	ap.add_argument("-b", "--buffer", type=int, default=64, help="max buffer size") #optional buffer to define the length of the tail
	args = vars(ap.parse_args())


	#define the lower and upper bouundaries of the color of the ball in the hsv color space then inititalize the list of tracked points
	pink = (164,183, 202)
	pinkLower = (159, 90,192)#(127,166,154)
	pinkUpper = (169, 183, 220)#(247,255,255)
	green = (43, 108, 214)
	greenLower = (29,86, 6)
	greenUpper = (64, 255, 255)
	
	
	
	trackedColorLower = greenLower
	trackedColorUpper = greenUpper

	#the list of tracked points for drawing a tail
	#decided to take this out, only used for debugging
	#pts = deque(maxlen=args["buffer"])

	#Resolution and max velocity values
	xRes = 1280
	yRes = 720
	xMaxVel = -50
	yMaxVel = 30
	
	
	
	#if a video path was not supplied grab the reference to the webcam
	if (not args.get("video", False)):
		camera = cv2.VideoCapture(1) #actually grabs the webcam (1) means my usb webcam (0) is built in webcam
		#tweak the resolution of the camera
		camera.set(3,xRes)
		camera.set(4,yRes)
		
	#otherwise grab a reference to the supplied video file
	#only used for debugging
	else:
		camera = cv2.VideoCapture(args["video"])
		
		
		
	#ARDUINO SETUP
	tracking = False
	scanning = False
	
	ser = serial.Serial('COM3', 9600, timeout=0)
	time.sleep(5)
	ser.reset_input_buffer() #<------- These two lines must be done everytime we write to serial
	ser.reset_output_buffer()#<------- Prevents the buffer from overflowing
	#tell the arduino to scan
	ser.write("scan.")
	ser.flush()
	
	#we are now scanning
	scanning = True
	frameCounter = 0
	lastTrackedFrame = 0
	
	#--------------------------------------------------------------------------------------------------
	#
	#MAIN LOOP
	#
	#--------------------------------------------------------------------------------------------------
	while True:
		#debug for displaying memory usage
		#process = psutil.Process(os.getpid())
		#print(process.memory_info().rss)
		#print "frameCounter:{} \tscanning:{} \ttracking:{}".format(frameCounter,scanning, tracking)
		#if we haven't seen the ball in 60 frames, send a message to go into scan
		if (frameCounter - lastTrackedFrame > 60 and tracking):
			tracking = False
			scanning = True
			ser.reset_input_buffer()
			ser.reset_output_buffer()
			ser.write("scan.")
			ser.flush()
			
		#grab the current frame
		(grabbed, frame) = camera.read() #returns a 2-tuple, 
		# first value is grabbed which is a boolean whether a frame was successfully read
		#frame is the video frame itself												
		
		#if we are viewing a video and we did not grab a frame then we have reached the end of the video
		if (args.get("video") and not grabbed):
			break
		#this is sloppy and should probably be changed, currently just handles a bad frame by dropping it on the floor
		if (not grabbed):
			print "skippedFrame"
			continue
		
		#preprocessing of frame. essentially drops the resolution to 600, making fps go up
		#convert the frame into the HSV color space
		hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
		
		#construct a binary mask for the tracked color, then perform a series of dilations and erosions to remove the small blobs left in the mask
		mask = cv2.inRange(hsv, trackedColorLower, trackedColorUpper)
		
		#EROSION AND DILATION
		mask = cv2.erode(mask, None, iterations=2)
		mask = cv2.dilate(mask, None, iterations=7)
		
		
		#compute the contour of our object and draw it in our frame
		#find contours in the mask and initialize the current (x,y) center of the object
		cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
		center = None
		
		#only proceed if at least one contour was found
		if (len(cnts) > 0):
			#find the largest contour in the mask, then use it to compute the minimum enclosing circle and centroid
			c = max(cnts, key=cv2.contourArea)
			((x,y), radius) = cv2.minEnclosingCircle(c)
			M = cv2.moments(c)
			#center 
			center = ( int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]) )
			#print center
			#only proceed if the radius meets a minimum size
			#helps reduce noise
			if (radius >25):
				
				#update the last time we tracked the ball to this frame
				lastTrackedFrame = frameCounter
				#if we were scanning we need to track
				if (scanning):
					ser.reset_output_buffer()
					ser.reset_input_buffer()
					ser.write("track.")
					ser.flush()
					tracking=True
					scanning=False
					
				#only check every 10 frames	
				if(tracking and frameCounter%10 ==0):
					xVel = calculateDistanceToMove(center[0], xRes, xMaxVel)
					yVel = calculateDistanceToMove(center[1], yRes, yMaxVel)
					#print "xVel:{}\t yVel:{}".format(xVel, yVel)
					ser.reset_output_buffer()
					ser.reset_input_buffer()
					ser.write("{},{}.".format(xVel,yVel))
					ser.flush()
					
				#draw the circle and the centroid on the frame, then update the list of tracked points
				cv2.circle(frame, (int(x), int(y)), int(radius), (0,0,255), 2)
				cv2.circle(frame, center, 5, (255,0, 255), -1)
		
		#debug
		#update the points queue that generates the tail
		#pts.appendleft(center)
		
		#debug not actually used because we are notdrawing a tail
		# loop over the set of tracked points
		for i in xrange(1, len(pts)):
			# if either of the tracked points are None, ignore
			# them
			if pts[i - 1] is None or pts[i] is None:
				continue
	 
			# otherwise, compute the thickness of the line and
			# draw the connecting lines
			thickness = int(np.sqrt(args["buffer"] / float(i + 1)) * 2.5)
			cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)
	 
		# show the mask 
		cv2.imshow("mask", mask)
		# show the frame to our screen
		cv2.imshow("Frame", frame)
		
		#super buggy. have to grab only 8 bits so it is not slow as hell
		#this is what causes the crash inside of the command prompt
		#listens for a keyboard interupt so we can quit the loop
		key = cv2.waitKey(1) & 0xFF
	 
		# if the 'q' key is pressed quit
		if (key == ord("q")):
			break
		
		frameCounter+=1
		#end of loop
	 
	# cleanup the camera and close any open windows
	camera.release()
	cv2.destroyAllWindows()

	
main()