import constants

import cv2
import colorsys
import imutils
import numpy as np

import keras_ocr.pipeline

THETA_THRESH = np.pi/45
RHO_THRESH = 25

class DocumentLines(object):
    class Line(object):
        def __init__(self, rho=None, t=None):
            self.rho = rho
            self.t = t
            self.sin = self.cos = None
            if t is not None:
                self.cos = np.cos(t)
                self.sin = np.sin(t)

        def dot_product(self, other) -> float:
            return np.arccos(np.clip(self.cos*other.cos + self.sin*other.sin, -1, 1))

        def get_intersection(self, other) -> tuple[int, int]:
            d = self.cos*other.sin - other.cos*self.sin
            if d != 0:
                x = (self.rho*other.sin - other.rho*self.sin)/d
                y = (self.cos*other.rho - other.cos*self.rho)/d
                return (int(x), int(y))
            return None

        def get_list(self) -> list:
            return [self.rho, self.t]

        def get_trig(self) -> list:
            return [self.cos, self.sin]

    # Even indices represents min rho line near similar theta lines. Odd represents max rho.
    def __init__(self, shape):
        self.width, self.height = shape
        self.lines = [None for _ in range(4)]

    # Only stores the minimum and maximum distance pairs of lines.
    def add_line(self, rho, theta):
        line = DocumentLines.Line(rho, theta)

        for id in range(0, len(self.lines), 2):
            if self.lines[id] is None:
                self.lines[id] = line
                break
            elif self.lines[id].dot_product(line) <= 5*THETA_THRESH:
                if self.lines[id + 1] is None:
                    self.lines[id + 1] = line
                    if self.lines[id].rho > self.lines[id + 1].rho:
                        self.lines[id], self.lines[id + 1] = self.lines[id+1], self.lines[id]
                elif self.lines[id].rho > rho:
                    self.lines[id] = line
                elif rho > self.lines[id + 1].rho:
                    self.lines[id + 1] = line
                break

    def document_found(self) -> bool:
        return self.lines[1] is not None and self.lines[3] is not None

    def get_lines(self) -> list:
        return [line.get_list() for line in self.lines if isinstance(line, DocumentLines.Line)]

    def get_trigs(self) -> list:
        return [line.get_trig() for line in self.lines if isinstance(line, DocumentLines.Line)]

    # Temporary testing function
    def draw_lines(self, img):
        for n, line in enumerate(self.lines):
            if isinstance(line, DocumentLines.Line):
                x0 = line.cos*line.rho
                y0 = line.sin*line.rho
                x1 = int(x0 + 1000*(-line.sin))
                y1 = int(y0 + 1000*(line.cos))
                x2 = int(x0 - 1000*(-line.sin))
                y2 = int(y0 - 1000*(line.cos))
                r, g, b = colorsys.hsv_to_rgb(n*0.1, 0.8, 1)
                cv2.line(img, (x1, y1), (x2, y2), (b*225, g*225, r*225), 2)

    # As a document, we should have four corners of the document to manipulate.
    def get_corners(self) -> np.ndarray:
        points = []

        # Compares 0w/2, 0w/3, 1w/2, 1w/3
        for id in range(len(self.lines)):
            p = self.lines[id//2].get_intersection(self.lines[id%2 + 2])
            if p is None:
                return None
            elif (0, 0) > p > (self.width, self.height):
                return None
            points.append(p)

        return np.array(points)

    def __str__(self):
        out = ""
        for id in range(len(self.lines)-1):
            out += f"{self.lines[id].get_list()}, "
        return out + f"{self.lines[-1].get_list()}"

class DocUtils:
    # Exception used to tell QtObjects that the document could not be found
    class NoDocumentDetectedError(Exception):
        pass

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

        # for letter paper ratio, w/h = 1.294
        max_height = int(max_width*constants.CROP_RATIO)

        # height_a = np.sqrt(((tr[0] - br[0])**2) + ((tr[1] - br[1])**2))
        # height_b = np.sqrt(((tl[0] - bl[0])**2) + ((tl[1] - bl[1])**2))
        # max_height = max(int(height_a), int(height_b))
        # max_height = max(int(max_width*1.294), max_height)

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, matrix, (max_width, max_height))

    def midpoint(a, b):
        return (int((a[0] + b[0])/2), int((a[1] + b[1])/2))

    # Returns original opencv image and the corners of the detected document.
    def get_document(path):
        org_img = cv2.imread(path)
        ratio = org_img.shape[0]/600.0
        img = imutils.convenience.resize(org_img.copy(), height=600)

        # Processes Image for Document Detection
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.morphologyEx(img.copy(), cv2.MORPH_CLOSE, kernel, iterations=5)
        frame = cv2.GaussianBlur(edges, (7, 7), 3)
        edges = cv2.addWeighted(edges, 2, frame, -1, 0)
        edges = cv2.cvtColor(edges, cv2.COLOR_BGR2GRAY)
        edges = cv2.GaussianBlur(edges, (11, 11), 0)
        edges = cv2.Canny(edges, 0, 100, apertureSize=3)

        # Processing HoughLines into the four most likely document items
        strong_lines = DocumentLines(img.shape[:2])
        lines = cv2.HoughLines(edges, 1, np.pi/180, 60)
        if lines is not None:
            # Parses HoughLine space into a list of positive rho lines
            lines = lines[:, 0].tolist()
            lines = [x if x[0] >= 0 else [-x[0], x[1]-np.pi] for x in lines]

            candid_lines = np.array([lines[0]])
            strong_lines.add_line(lines[0][0], lines[0][1])

            for line in lines[1:]:
                rho, theta = line[0], line[1]

                closeness_rho = np.isclose(rho, candid_lines[:,0], atol=RHO_THRESH)
                closeness_theta = np.isclose(theta, candid_lines[:,1], atol=THETA_THRESH)

                isclose = np.all([closeness_rho, closeness_theta], 0)

                if not any(isclose):
                    candid_lines = np.concatenate((candid_lines, [line]))
                    strong_lines.add_line(rho, theta)
                    
                    if strong_lines.document_found():
                        break   

        if not strong_lines.document_found() or strong_lines.get_corners() is None:
            raise DocUtils.NoDocumentDetectedError

        return org_img, strong_lines.get_corners()*ratio

    # Returns the mask to inpaint on the cropped image.
    def get_text_mask(img, pipeline: keras_ocr.pipeline.Pipeline):
        r = img.shape[0]/1200
        pred_img = imutils.convenience.resize(img.copy(), height=1200)
        prediction_data = pipeline.recognize([pred_img])

        mask = np.zeros(img.shape[:2], dtype='uint8')
        for box in prediction_data[0]:
            pos = [(box[1][i][0]*r, box[1][i][1]*r) for i in range(4)]
            thickness = int(np.sqrt((pos[2][0] - pos[1][0])**2 + (pos[2][1] - pos[1][1])**2))
            cv2.line(mask, DocUtils.midpoint(pos[1], pos[2]), DocUtils.midpoint(pos[0], pos[3]), 255, thickness)
        return mask

    def get_resized_final(img, mask):
        resized = cv2.inpaint(img, mask, 7, cv2.INPAINT_NS)
        return imutils.convenience.resize(resized, height=600)