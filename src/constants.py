import numpy as np

ACCEPTABLE_FILES = ['png', 'jpg', 'jpeg']
ACCEPTABLE_FILE_DIALOG = (''.join([f"*.{x} " for x in ACCEPTABLE_FILES]))[:-1]

# Used in detection.py
CROP_RATIO = 1.545  
RATIO_BASE      = 1.45
RATIO_SIGMA     = 0.15
THETA_THRESH    = np.pi/90
RHO_THRESH      = 25
LINE_THRESH     = 5*np.pi/45
CANNY_SIGMA     = 0.4
RECTNESS_SIGMA  = 0.01

SAVE_WIDTH = 1000