import numpy as np
import cv2
from feature_extractor.KalmanFilter import KalmanFilter

class HumanKeypointsFilter:
    """
    1. Gaussian blur (optional)
    2. Minimal Filter
    3. Projection to camera coodinate
    4. Kalman Filter
    
    NOTE: Vectorization calculation would be much faster
    """
    def __init__(self, id, 
                 gaussian_blur: bool = True,
                 minimal_filter: bool = True,
                 ) -> None:
        """
        required: id
        optional: gaussian_blur, minimal_filter
        """
        self.id = id
        self.keypoints_filtered: np.ndarray = None              # 3D keypoints [K,3]
        self.missing_count: int = 0
        self.valid_keypoints: np.ndarray                        # valid keypoint mask
        
        
        self.gaussian_blur = gaussian_blur
        self.minimal_filter = minimal_filter
        
        self.filters = None

    def gaussianBlur_depth(self, depth_frame: np.ndarray, kernel_size=(11,11)) -> np.ndarray:
        """
        @depth_frame: [axis_0, axis_1]
        @kernel_size: (m,m)
        """
        return cv2.GaussianBlur(depth_frame, kernel_size)
    
    def minimalFilter(self, depth_frame, keypoint_pixel, kernel_size=(11,11)) -> np.ndarray:
        """
        @keypoint_pixel: [K,3]
        """
        shape = cv2.MORPH_RECT
        kernel = cv2.getStructuringElement(shape, kernel_size)
        img_shape = depth_frame.shape
        width, height = kernel[1] - 1 >> 1, kernel[0] - 1 >> 1
        for keypoint_pos in keypoint_pixel[:, :2]:
            left = keypoint_pos[1] - width
            right = keypoint_pos[1] + width
            top = keypoint_pos[0] - height
            bottom = keypoint_pos[0] + height
            # check if out of boundary
            if left < 0 or right > img_shape[1] or top < 0 or bottom > img_shape[0]:
                break
            depth_frame = cv2.erode(depth_frame[left:left+height, top:top+height], kernel)
            
        return depth_frame
        
        
    def align_depth_with_color(self, keypoints_2d, depth_frame, intrinsic_mat, rotate = cv2.ROTATE_90_CLOCKWISE):
        """
        @keypoints_2d: [K, 3(x,y,conf)]. x=y=0.00 with low conf means the keypoint does not exist
        @depth_frame: []
        @intrinsic_mat: cameara intrinsic K
        @rotate = 0 | None
        
        Mask: self.valid_keypoints
        return keypoints in camera coordinate [K,3]
        """
        # valid keypoints mask
        valid_xy = keypoints_2d[:,:2] != 0.00        # bool [K,2]
        self.valid_keypoints = valid_xy[:,0] & valid_xy[:,1]  # bool vector [K,]

        # check rotation
        if rotate == cv2.ROTATE_90_CLOCKWISE:
            axis_0 = depth_frame.shape[0] - keypoints_2d[:, 0:1]  # vector [K,]
            axis_1 = keypoints_2d[:, 1:2]                         # vector [K,]
        else:
            # no ratation
            axis_0 = keypoints_2d[:, 1:2]
            axis_1 = keypoints_2d[:, 0:1]
        
        axis_2 = np.ones_like(axis_0)

        keypoints_pixel = np.concatenate((axis_0, axis_1, axis_2), axis=1).astype(np.int16)     # [K, 3]
        
        # Preprocessing Filters
        if self.gaussian_blur:
            depth_frame = self.gaussianBlur_depth(depth_frame)
        if self.minimal_filter:
            depth_frame = self.minimalFilter(depth_frame, keypoints_pixel)
        
        keypoints_depth = depth_frame[keypoints_pixel[:,0], keypoints_pixel[:,1]]               # [K,]
        #                   [3,3]           [3,K]               [K,K]
        raw_keypoints_cam = intrinsic_mat @ keypoints_pixel.T @ np.diag(keypoints_depth)            # [3, K]
        return raw_keypoints_cam.T    #[K,3]
    
    
    def kalmanfilter_cam(self, raw_keypoints_cam: np.ndarray, freq: float = 30.0):
        """
        @ raw_keypoints_cam: keypoints to be filtered [K,3]
        @ freq: Kalman Filter updation frequency
        return: keypoints_filtered [K,3]
        """
        K, D = raw_keypoints_cam.shape
        keypoints_filtered = np.zeros_like(raw_keypoints_cam)
        
        if self.filters == None:
            # init keypoint kalman filter
            self.filters = np.empty(K, dtype=object)
            # NOTE: need vectorization?
            for k in range(K):
                self.filters[k] = KalmanFilter(freq=freq)
                self.filters[k].initialize(raw_keypoints_cam[k])        # raw_keypoints_cam[k] is a xyz vector
                keypoints_filtered[k] = self.filters[k].getMeasAfterInitialize()
        else:
            for k in range(K):
                keypoints_filtered[k] = self.filters[k].update(raw_keypoints_cam[k])
        
        return keypoints_filtered

