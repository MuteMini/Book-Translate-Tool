from enum import Enum, auto
from PyQt6.QtCore import pyqtSignal

class View(Enum):
    UPLOAD   = auto()
    LOAD     = auto()
    RESULT   = auto()
    EDIT_CROP = auto()
    EDIT_TEXT = auto()
    MERGE    = auto()

class ViewWidget:
    swap = pyqtSignal(View)
