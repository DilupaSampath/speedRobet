# USAGE
# python pi_object_detection.py --prototxt MobileNetSSD_deploy.prototxt.txt --model MobileNetSSD_deploy.caffemodel

# import the necessary packages
from imutils.video import VideoStream
from imutils.video import FPS
from multiprocessing import Process
from multiprocessing import Queue
import numpy as np
import argparse
import imutils
import time
import cv2
import serial

# ser = serial.Serial('ttyACM1', baudrate = 9600, timeout=1)
port = '/dev/ttyACM2'
ard = serial.Serial(port,9600)
def classify_frame(net, inputQueue, outputQueue):
	# keep looping
	while True:
		# check to see if there is a frame in our input queue
		if not inputQueue.empty():
			# grab the frame from the input queue, resize it, and
			# construct a blob from it
			frame = inputQueue.get()
			frame = cv2.resize(frame, (300, 300))
			blob = cv2.dnn.blobFromImage(frame, 0.007843,
				(300, 300), 127.5)

			# set the blob as input to our deep learning object
			# detector and obtain the detections
			net.setInput(blob)
			detections = net.forward()

			# write the detections to the output queue
			outputQueue.put(detections)

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", required=True,
	help="path to Caffe 'deploy' prototxt file")
ap.add_argument("-m", "--model", required=True,
	help="path to Caffe pre-trained model")
ap.add_argument("-c", "--confidence", type=float, default=0.1,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())
faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
tracker_type='CSRT'
tracker = cv2.TrackerMOSSE_create()
# load our serialized model from disk
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

# initialize the input queue (frames), output queue (detections),
# and the list of actual detections returned by the child process
inputQueue = Queue(maxsize=1)
outputQueue = Queue(maxsize=1)
detections = None

# construct a child process *indepedent* from our main process of
# execution
print("[INFO] starting process...")
p = Process(target=classify_frame, args=(net, inputQueue,
	outputQueue,))
p.daemon = True
p.start()

# initialize the video stream, allow the cammera sensor to warmup,
# and initialize the FPS counter
print("[INFO] starting vidfpseo stream...")
vs = VideoStream(src=0).start()
# vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)
fps = FPS().start()
xV=None
co = True
Interrup=False
InterrupInside=False
neckState=True
lastState=-1
# loop over the frames from the video stream
while True:
	# grab the frame from the threaded video stream, resize it, and
	# grab its imensions
	frame = vs.read()
	if(len(frame)>0):
		frame = imutils.resize(frame, width=400)
		(fH, fW) = frame.shape[:2]

		# if the input queue *is* empty, give the current frame to
		# classify
		if inputQueue.empty():
			inputQueue.put(frame)

		# if the output queue *is not* empty, grab the detections
		if not outputQueue.empty():

			detections = outputQueue.get()
		# check to see if our detectios are not None (and if so, we'll
		# draw the detections on the frame)
		if detections is not None:
			# loop over the detections
			for i in np.arange(0, detections.shape[2]):
				# extract the confidence (i.e., probability) associated
				# with the prediction
				confidence = detections[0, 0, i, 2]

				# filter out weak detections by ensuring the `confidence`
				# is greater than the minimum confidence
				# if confidence < args["confidence"]:
				# 	continue

				# otherwise, extract the index of the class label from
				# the `detections`, then compute the (x, y)-coordinates
				# of the bounding box for the object
				idx = int(detections[0, 0, i, 1])
				dims = np.array([fW, fH, fW, fH])
				box = detections[0, 0, i, 3:7] * dims
				gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
				# (startX, startY, endX, endY) = box.astype("int")
				# faces = faceCascade.detectMultiScale(
			    #     gray,
			    #     scaleFactor=1.1,
			    #     minNeighbors=5,
			    #     minSize=(35, 35)
			    # )
				# print(len(faces))
				# print("len(faces)")
				if Interrup and ((CLASSES[idx] == 'person')):
					xV = tuple(box)
					tracker.init(gray, xV)
					Interrup=False
					InterrupInside=True
				(success, box) = tracker.update(gray)
				if success:
					if xV is not None and InterrupInside:
						# Interrup=False
						(x, y, w, h) = [int(v) for v in box]
						cv2.rectangle(frame, (x, y), (x + w, y + h),
						(0, 255, 0), 2)
						newX=x
						newY=y
						print("X ---> "+str(newX))
						print("Y ----> "+str(newY))
						if newX<= 50 and newX>=0 and lastState !=0:
							# ard = serial.Serial(port,9600)
							ard.write('stop\r\n'.encode())
							# ard.close()
							neckState=True
							print('middle')
							lastState=0
						elif newX <= 0 and neckState:
							# ard = serial.Serial(port,9600)
							# ard.write('stop\r\n'.encode())
							ard.write('neck_left\r\n'.encode())
							# ard.close()
							print('neck_left ****************************')
							# time.sleep(10.0)
							neckState=False
							lastState=-1
						elif newX >=100 and neckState:
							# ard = serial.Serial(port,9600)
							# ard.write('stop\r\n'.encode())
							ard.write('neck_right\r\n'.encode())
							# ard.close()
							print('neck_right $$$$$$$$$$$$$$$$$$$$$$$$$$$')
							# time.sleep(10.0)
							neckState=False
							lastState=1
						else:
							a =1
						Interrup=False
		# show the output frame
		cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF

	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
	if key == ord("s"):
		Interrup=True
		# print('innnn')
	# update the FPS counter
	fps.update()

# stop the timer and display FPS information
fps.stop()
# print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
# print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
