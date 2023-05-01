import numpy as np

ACCEPTABLE_FILES = ['png', 'jpg', 'jpeg']
ACCEPTABLE_FILE_DIALOG = (''.join([f"*.{x} " for x in ACCEPTABLE_FILES]))[:-1]

# Used in detection.py
CROP_RATIO = 1.545
THETA_THRESH = np.pi/45
RHO_THRESH = 25

LINE_THRESH = 5*THETA_THRESH
