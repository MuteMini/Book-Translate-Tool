import constants

import cv2, colorsys, imutils, numpy as np
from PIL import Image

import keras_ocr.pipeline

class Line(object):
    def __init__(self, rho=None, t=None):
        self.rho = rho
        self.t = t
        self.sin = self.cos = None
        if t is not None:
            self.sin = np.sin(t)
            self.cos = np.cos(t)

    def __gt__(self, other):
        return self.rho > other.rho

    def dot_product(self, other) -> float:
        return np.arccos(np.clip(self.cos*other.cos + self.sin*other.sin, -1, 1))
    
    def intersection(self, other) -> tuple[int, int]:
        d = self.cos*other.sin - other.cos*self.sin
        if d == 0:
            return None
        x = (self.rho*other.sin - other.rho*self.sin)/d
        y = (self.cos*other.rho - other.cos*self.rho)/d
        return (int(x), int(y))
    
class Document(object):
    # i and i+1 index represents min rho line near similar theta lines.
    def __init__(self, shape: tuple[int,int]):
        self.width, self.height = shape
        self.lines = [None for _ in range(4)]

    def add_line(self, rho, theta):
        line = Line(rho, theta)
        new_index = -1
        new_lines = [None for _ in range(len(self.lines))]

        for i in range(0, len(self.lines), 2):
            if self.lines[i] is None:
                self.lines[i] = line
                break
            
            if self.lines[i].dot_product(line) > constants.LINE_THRESH:
                continue

            if self.lines[i+1] is None:
                if self.lines[i] > line:
                    self.lines[i+1] = self.lines[i]
                    self.lines[i] = line
                else:
                    self.lines[i+1] = line
            else:
                self.lines[i] = line if self.lines[i] > line else self.lines[i]
                self.lines[i+1] = line if line > self.lines[i+1] else self.lines[i+1]
            break

    def document_found(self):
        return self.lines[1] is not None and self.lines[3] is not None

    def corners(self, this_bound=None) -> np.ndarray:
        points = []
        lines = self.lines if this_bound is None else this_bound

        for i in range(4): 
            p = lines[i//2].intersection(lines[i%2 + 2])
            if p is None or (0, 0) > p > (self.width, self.height):
                return None
            points.append(p)
        return points
    
class DocUtils:
    # Comes from https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example
    # Sorts points into tl, tr, br, bl
    def order_point(pts) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")

        # tl, br has max sum of points
        s = np.sum(pts, axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # tr, bl has most difference in points
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]

        return rect

    # Comes from https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example
    # Performs four point transformation after the document corners are found
    def crop_document(img, pts) -> cv2.Mat:
        rect = DocUtils.order_point(pts)
        tl, tr, br, bl = rect

        width_a = np.sqrt(((br[0] - bl[0])**2) + ((br[1] - bl[1])**2))
        width_b = np.sqrt(((tr[0] - tl[0])**2) + ((tr[1] - tl[1])**2))
        max_width = max(int(width_a), int(width_b))

        # Transforms to letter paper ratio, w/h = 1.294
        max_height = int(max_width*constants.CROP_RATIO)

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, matrix, (max_width, max_height))

    def midpoint(a, b):
        return (int((a[0] + b[0])/2), int((a[1] + b[1])/2))
    
    # Returns original image and corners of detected document
    def find_document(path):
        original = cv2.imread(path)
        ratio = original.shape[0] / 600

        image = imutils.convenience.resize(original.copy(), height=600)
        edges = image.copy()

        # Image processing for HoughLine
        # edges = cv2.fastNlMeansDenoising(edges, h=7)
        kernel = np.ones((5,5), np.uint8)
        edges = cv2.morphologyEx(image.copy(), cv2.MORPH_CLOSE, kernel, iterations=1)
        frame = cv2.GaussianBlur(edges, (7,7), 5)
        edges = cv2.addWeighted(edges, 2.5, frame, -1.5, 0)
        edges = cv2.GaussianBlur(edges, (7,7), 0)

        # From https://stackoverflow.com/questions/41893029/opencv-canny-edge-detection-not-working-properly
        v = np.median(edges)
        lower = int(max(0, (1.0 - constants.CANNY_SIGMA)*v))
        upper = int(min(255, (1.0 + constants.CANNY_SIGMA)*v))
        edges = cv2.Canny(edges, lower, upper, apertureSize=3)

        # Processing HoughLines to find most likely document lines
        strong_lines = Document(image.shape[:2])
        lines = cv2.HoughLines(edges, 1, np.pi/180, 60)
        if lines is not None:
            # Turns all lines into positive rho
            lines = lines[:, 0].tolist()
            lines = [x if x[0] >= 0 else [-x[0], x[1]-np.pi] for x in lines]

            candids = np.array([lines[0]])
            strong_lines.add_line(lines[0][0], lines[0][1])

            for line in lines[1:]:
                rho, theta = line[0], line[1]
                
                closeness_rho = np.isclose(rho, candids[:,0], atol=constants.RHO_THRESH)
                closeness_theta = np.isclose(theta, candids[:,1], atol=constants.THETA_THRESH)

                isclose = np.all([closeness_rho, closeness_theta], 0)

                if not any(isclose):
                    candids = np.concatenate((candids, [line]))
                    strong_lines.add_line(rho, theta)

        corners = np.array([(0,0), (original.shape[1], 0), (0, original.shape[0]), (original.shape[1], original.shape[0])])
        if strong_lines.document_found() and strong_lines.corners() is not None:
            corners = np.multiply(strong_lines.corners(), ratio)

        return original, corners
    
    def text_mask(image, pipeline: keras_ocr.pipeline.Pipeline):
        ratio = image.shape[0] / 1200

        prediction_image = imutils.convenience.resize(image.copy(), height=1200)
        prediction_data = pipeline.recognize([prediction_image])

        mask = np.zeros(image.shape[:2], dtype='uint8')
        for box in prediction_data[0]:
            bounds = box[1]
            pos = [(bounds[i][0]*ratio, bounds[i][1]*ratio) for i in range(4)]
            thickness = int(np.sqrt((pos[2][0] - pos[1][0])**2 + (pos[2][1] - pos[1][1])**2))
            cv2.line(mask, DocUtils.midpoint(pos[1], pos[2]), DocUtils.midpoint(pos[0], pos[3]), 255, thickness)
        return mask
    
    def resized_final(image, mask, height=None, width=None):
        resized = cv2.inpaint(image, mask, 7, cv2.INPAINT_NS) if mask is not None else image

        if height is None:
            resized = imutils.convenience.resize(resized, width=width)
        if width is None:
            resized = imutils.convenience.resize(resized, height=height)
        return resized
    
    def opencv_to_pil(image):
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
