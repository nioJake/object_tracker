from collections import deque
from enum import Enum
import numpy as np
import imutils
import cv2

from nio.block.base import Block, Signal
from nio.properties import Property, VersionProperty, ListProperty, \
    BoolProperty, PropertyHolder, SelectProperty, StringProperty, IntProperty


class FilterTypes(Enum):
    hsv = 'HSV'
    #rgb = 'RGB'

class ImageFilters(PropertyHolder):
    obj = StringProperty(title='Object name', default='TrackMe')
    filter_type = SelectProperty(FilterTypes,
                                 title='Filter type',
                                 default=FilterTypes.hsv)
    filter_lo = Property(title='Lower bounds for image filter',
                         default='',
                         allow_none=True)
    filter_hi = Property(title='Upper bounds for image filter',
                         default='',
                         allow_none=True)

class TrackObjects(Block):

    version = VersionProperty('2.0.0')
    ipcam = BoolProperty(title='Use IP Camera?', default=False)
    camera = IntProperty(title='Camera Index', default=0)
    ipcam_address = StringProperty(title='IP Camera Address',
                                   default='',
                                   allow_none=True)
    video_ref = StringProperty(title='Path to video file',
                               default='',
                               allow_none=True)
    filters = ListProperty(ImageFilters,
                           title='Filters',
                           default=[])

    def __init__(self):
        super().__init__()
        self.video_capture = None

    def start(self):
        if not self.ipcam() and self.video_ref() == None:
            self.video_capture = cv2.VideoCapture(0)
        else:
            self.video_capture = cv2.VideoCapture(self.video_ref())

    def process_signals(self, signals):
        counter = 0
        (dX, dY) = (0, 0)
        direction = ""

        for signal in signals:
            try:
                (grabbed,frame) = self.video_capture.read()
            except:
                break
            if (not grabbed):
                break

            frame = imutils.resize(frame, width=600)
            blurred = cv2.GaussianBlur(frame, (11, 11), 0)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # construct a mask and perform dialations and erosions to remove
            # any small blobs left in the mask

            for each in self.filters():
                mask = cv2.inRange(hsv, tuple(each.filter_lo()),
                                    tuple(each.filter_hi()))
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)

                # find contours in the mask and initialize the current center
                cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
            		                    cv2.CHAIN_APPROX_SIMPLE)[-2]

                if len(cnts)>0:
            		# find the largest contour in the mask,
                    # then use to find centroid
                    c = max(cnts, key=cv2.contourArea)
                    ((x, y), radius) = cv2.minEnclosingCircle(c)
                    M = cv2.moments(c)
                    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
            		# only proceed if the radius meets a minimum size
                    if radius > 10:
            			# draw the circle and centroid on the frame & update points
                        cv2.circle(frame, (int(x), int(y)), int(radius),
    	                   (0, 255, 255), 2)
                        cv2.circle(frame, center, 5, (0, 0, 255), -1)

                	# update the points queue
                    track_center = {
                        'object': each.obj(),
                        'x_coord': center[0],
                        'y_coord': center[1]
                    }
                    sig = Signal({
                    "track" : track_center
                    })
                    self.notify_signals([sig])

                else:
                    sig = Signal({
                    "track" : None
                    })
                    self.notify_signals([sig])