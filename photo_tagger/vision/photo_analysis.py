from ... import utils
import cv2
import numpy as np
from SSH.ssh_detector import SSHDetector
from mtcnn_detector import MtcnnDetector

class VectorExtractor:
    '''
        This class provides functionality for retrieving descriptors for each face in image
    '''
    def __init__(self, recognition_model_path, ssh_model_path,
                    mtcnn_model_path, scales, detection_threshold):
        self.extractor = Embedding(recognition_model_path, 0)
        self.detector = SSHDetector(ssh_model_path, 0)
        self.mtcnn_detector = MtcnnDetector(mtcnn_model_path)
        self.scales = scales
        self.detection_threshold = detection_threshold
        
    def _preprocess(self, img):
        im_shape = img.shape
        target_size = self.scales[0]
        max_size = self.scales[1]
        im_size_min = np.min(im_shape[0:2])
        im_size_max = np.max(im_shape[0:2])
        if im_size_min>target_size or im_size_max>max_size:
            im_scale = float(target_size) / float(im_size_min)
            # prevent bigger axis from being more than max_size:
            if np.round(im_scale * im_size_max) > max_size:
                im_scale = float(max_size) / float(im_size_max)
            img = cv2.resize(img, None, None, fx=im_scale, fy=im_scale)
        return img

    @utils.SingleExec()
    def _detect(self, image):
        face_rects = self.detector.detect(image, threshold = self.detection_threshold)
        return face_rects

    @uitls.SingleExec()
    def _predict(self, img, landmarks):
        return self.extractor.get(img, landmarks)

    def retrieve(self, img_path):
        img = cv2.imread(img_path)
        img = self._preprocess(img)
        faces = self._detect(img)

        vectors = []

        for face in faces:
            w = face[2] - face[0]
            h = face[3] - face[1]
            wc = int( (face[2]+face[0])/2 )
            hc = int( (face[3]+face[1])/2 )
            size = int(max(w, h)*1.3)
            scale = 100.0/max(w,h)
            M = [ 
                [scale, 0, 64-wc*scale],
                [0, scale, 64-hc*scale],
            ]
            M = np.array(M)
            IM = cv2.invertAffineTransform(M)

            ebox = cv2.warpAffine(img, M, (128, 128))

            results = self.mtcnn_detector.detect_face(ebox)

            if results is None:
                continue

            bboxes, landmark = results

            landmark5 = np.zeros( (5,2) , dtype=np.float32 )

            for l in range(5):
                point = np.ones( (3,), dtype=np.float32)
                point[0:2] = [landmark[0][l], landmark[0][l+5]]
                point = np.dot(IM, point)
                landmark5[l] = point[0:2]

            feat = self._predict(img, landmark5)
            vectors.append(feat)

        return vectors

        