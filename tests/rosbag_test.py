# -*- coding: utf-8 -*-

# Copyright 2016 Massachusetts Institute of Technology

"""Extract images from a rosbag.
"""

import os
import argparse
import numpy as np
import cv2

import rosbag


# try: 
#     import ros_numpy
# except AttributeError:
#     import numpy as np
#     np.float = np.float64  # temp fix for following import
#     import ros_numpy


from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from ultralytics import YOLO
from ultralytics.engine.results import Results


model = YOLO('models/yolov8m-pose.pt')



def main():
    """Extract a folder of images from a rosbag.
    """
    # parser = argparse.ArgumentParser(description="Extract images from a ROS bag.")
    # parser.add_argument("bag_file", help="Input ROS bag.")
    # parser.add_argument("output_dir", help="Output directory.")
    # parser.add_argument("image_topic", help="Image topic.")

    # args = parser.parse_args()

    # print "Extract images from %s on topic %s into %s" % (args.bag_file,
    #                                                       args.image_topic, args.output_dir)
    bag_file = "/home/xmo/bagfiles/RGBD.bag"
    image_topic = "/camera/color/image_raw"
    depth_topic = "/camera/aligned_depth_to_color/image_raw"
    output_dir = "/home/xmo/bagfiles/extract/"

    bag = rosbag.Bag(bag_file, "r")
    bridge = CvBridge()
    count = 0
    img_c = 0
    dep_c = 0
    for topic, msg, t in bag.read_messages(topics=[image_topic, depth_topic]):
        # print('seq:',msg.header.seq, '      TOPIC:',topic, '     T:', t, )

        if topic == depth_topic:
            depth_frame = bridge.imgmsg_to_cv2(msg)
            print('depth:',depth_frame.shape)       # [720,1280]

        if topic == image_topic:
            cv_img = bridge.imgmsg_to_cv2(msg)
            # print(type(cv_img))
            # print('color:',cv_img.shape)            # [720,1280,3]
            cv_img = cv2.rotate(cv_img, cv2.ROTATE_90_CLOCKWISE)
            # print(cv_img.shape)
            
            results = model.predict(cv_img)
            res = results[0]

            # print(results[0].keypoints.shape)
            # cv_img = results[0].plot()
            # # cv2.imshow('RealSense RGB',cv_img)
            # key = cv2.waitKey(100)
            # if key == ord('q'):
            #     break

            if results[0].keypoints.shape[0] in (1,2) and results[0].keypoints.shape[1] != 0:
                print(res.keypoints.data.shape)
                print(type(res.keypoints.data[0,0,0]))
                break
            #     aaaaa = results[0].keypoints
            #     print(type(aaaaa.data))
            #     print(results[0].keypoints)
                # np.save("/test/keypoint", results[0].keypoints)

        # cv2.imwrite(os.path.join(output_dir, "frame%06i.png" % count), cv_img)
        # print "Wrote image %i" % count

        count += 1

if __name__ == '__main__':
    main()