import cv2
import colorsys
import imutils
import numpy as np
from dataclasses import dataclass
import pytesseract
from PIL import Image
import os

MULT = 5
THETA_THRESH = np.pi/45
RHO_THRESH = 25

class DocumentLines(object):

    @dataclass
    class Line:
        rho: int = None
        t: float = None

        def dot_product(self, other) -> float:
            return np.arccos(np.clip(np.dot([np.cos(self.t), np.sin(self.t)], [np.cos(other.t), np.sin(other.t)]), -1, 1))

        def get_list(self) -> list:
            return [self.rho, self.t]
            
    # Even index (0, 2) represent min rho line on that "range" of lines. Odd represents max rho.
    def __init__(self):
        self.lines = [DocumentLines.Line() for _ in range(4)]
    
    # Only stores the minimum and maximum distance pairs of lines.
    def add_line(self, rho, theta):
        line = DocumentLines.Line(rho, theta)
        # Checks first pair to see if line fits there, then stores on the second pair.
        for id in range(0, len(self.lines), 2):
            if self.lines[id].t is None:
                self.lines[id] = line
                break
            elif self.lines[id].dot_product(line) <= 5*THETA_THRESH: #need to edit this value around
                if self.lines[id+1].rho is None:
                    self.lines[id+1] = line
                    if self.lines[id].rho > self.lines[id+1].rho:
                        self.lines[id], self.lines[id+1] = self.lines[id+1], self.lines[id]
                elif min(self.lines[id].rho, rho) == rho:
                    self.lines[id] = line
                elif max(self.lines[id+1].rho, rho) == rho:
                    self.lines[id+1] = line
                break

    def document_found(self) -> bool:
        return self.lines[1].rho != None and self.lines[3].rho != None
    
    def get_lines(self) -> list:
        list = []
        for id in range(len(self.lines)):
            list.append( self.lines[id].get_list() )
        return list

    # Temporary testing function
    def draw_lines(self, img: cv2.Mat):
        for n, line in enumerate(self.get_lines()):
            rh, t = line[0], line[1]
            a, b = np.cos(t), np.sin(t)
            x0 = a*rh
            y0 = b*rh
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))
            r, g, b = colorsys.hsv_to_rgb(n*0.05, 1, 0.8)
            n += 1
            cv2.line(img, (x1,y1), (x2,y2), (b*225,g*225,r*225), 2)

    def get_intersections(self) -> np.ndarray:
        list = np.array(self.get_lines())
        x_val = np.cos(list[:,1])
        y_val = np.sin(list[:,1])

        points = []

        for id in range(len(self.lines)):
            l1 = id//2
            l2 = id%2 + 2
            d = x_val[l1]*y_val[l2] - x_val[l2]*y_val[l1]
            if d != 0:
                x_p = (list[l1, 0]*y_val[l2] - list[l2, 0]*y_val[l1])/d
                y_p = (x_val[l1]*list[l2, 0] - x_val[l2]*list[l1, 0])/d 
                points.append((int(x_p), int(y_p)))

        if len(points) > 0:
            return np.array(points)
        return None

    def __str__(self):
        out = ""
        for id in range(len(self.lines)-1): 
            out += f"{self.lines[id].get_list()}, "
        return out + f"{self.lines[-1].get_list()}"

# Below functions come from https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/
# Performs four point transformation after the document corners are found
class pyImageSearch:
    # Sorts points into tl, tr, br, bl
    def order_point(pts) -> np.ndarray:
        rect = np.zeros((4,2), dtype="float32")

        # tl, br has max sum of points 
        s = np.sum(pts, axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        # tr, bl has most difference in points

        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        
        return rect

    # Performs the point transform on the image, returning the new image.
    def four_point_transform(image: cv2.Mat, pts) -> cv2.Mat:
        rect = pyImageSearch.order_point(pts)
        tl, tr, br, bl = rect

        width_a = np.sqrt( ((br[0] - bl[0])**2) + ((br[1] - bl[1])**2) )
        width_b = np.sqrt( ((tr[0] - tl[0])**2) + ((tr[1] - tl[1])**2) )
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt( ((tr[0] - br[0])**2) + ((tr[1] - br[1])**2) )
        height_b = np.sqrt( ((tl[0] - bl[0])**2) + ((tl[1] - bl[1])**2) )
        max_height = max(int(height_a), int(height_b))
        max_height = max(int(max_width*1.294), max_height)

        dst = np.array([ 
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype="float32")
        
        matrix = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, matrix, (max_width, max_height))

# path = 'hardertest.jpg'
path = 'hardtest.jpg'
# path = 'test.jpg'
# path = 'test2.jpg'
org_img = cv2.imread(path)

ratio = org_img.shape[0] / 600.0
img = imutils.convenience.resize(org_img.copy(), height = 600)
cv2.imshow("Original Image", img)
cv2.waitKey(0)

# Close Operation, to merge colors
kernel = np.ones((5, 5), np.uint8)
img: cv2.Mat = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel, iterations = 5)

# Unsharpen Masking
frame = cv2.GaussianBlur(img.copy(), (7,7), 3)
cv2.addWeighted(img, 2, frame, -1, 0, img)

# Canny Edge Detection, preps image for Hough Line Transforming
edges = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2GRAY)
edges = cv2.GaussianBlur(edges, (11,11), 0)
edges = cv2.Canny(edges, 0, 100, apertureSize=3)
cv2.imshow("Canny Image", edges)
cv2.waitKey(0)

# Processing HoughLines into the four most likely document items
candid_lines = 0
strong_lines = DocumentLines()
lines = cv2.HoughLines(edges, 1, np.pi/180, 60)
if lines is not None:
    lines = lines[:,0].tolist()
    lines = [x if x[0] >= 0 else [x[0]*-1.0, x[1]-np.pi] for x in lines]

    candid_lines = np.array([lines[0]])
    strong_lines.add_line(lines[0][0], lines[0][1])

    for line in lines[1:]:
        rho, theta = line[0], line[1]
        closeness_rho = np.isclose(rho, candid_lines[:,0], atol=RHO_THRESH)
        closeness_theta = np.isclose(theta, candid_lines[:,1], atol=THETA_THRESH)

        isclose = np.all([closeness_rho, closeness_theta], 0)

        if not any(isclose):
            strong_lines.add_line(rho, theta)
            candid_lines = np.concatenate((candid_lines, [line]))

        if strong_lines.document_found():
            break

print(strong_lines)

if strong_lines.document_found():
    strong_lines.draw_lines(img)
    for point in strong_lines.get_intersections():
        cv2.circle(img, point, 4, (255,255,0), 2)

    cutout = pyImageSearch.four_point_transform(org_img, strong_lines.get_intersections() * ratio)
    dir = os.getcwd() + "/final.jpg"
    cv2.imwrite(dir, cutout)

    letters = pytesseract.image_to_string(Image.fromarray(cutout), lang='eng+kor', config='--psm 11')
    print(letters)

cv2.imshow("Final Document", img)
cv2.waitKey(0)