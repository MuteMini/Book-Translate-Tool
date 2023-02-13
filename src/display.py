from views import View, ViewWidget

from PyQt6.QtCore import (
    Qt, pyqtSignal, QFileInfo
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QFileDialog, QGridLayout, QVBoxLayout, 
    QStyle
)
from PyQt6.QtGui import (
    QDragMoveEvent
)

ACCEPTABLE_FILES = ['png', 'jpg', 'jpeg']

class UploadWidget(QWidget, ViewWidget):
    filesRecieved = pyqtSignal(list)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self._button = QPushButton()
        self._button.setText("Add Files")
        self._button.clicked.connect(self._getFile)

        self._uploadIcon = QLabel()
        fileDiag = self.style().standardIcon( QStyle.StandardPixmap.SP_FileDialogStart )
        self._uploadIcon.setPixmap( fileDiag.pixmap(50, 50) )
        self._uploadIcon.setGeometry(50, 50, 50, 50)

        buttonLayout = QVBoxLayout()
        buttonLayout.addWidget(self._button)

        gridLayout = QGridLayout()
        gridLayout.addWidget(self._uploadIcon, 0, 0, Qt.AlignmentFlag.AlignHCenter)
        gridLayout.addLayout(buttonLayout, 1, 0)
        self.setLayout(gridLayout)

    def _getFile(self):
        fileName = QFileDialog.getOpenFileNames(self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
        self.filesRecieved.emit(fileName[0])
        self.swap.emit(View.Load)

    def dragEnterEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

            # Parse all the files and make sure there are only images.
            links = []
            onlyImgs = True

            for r in event.mimeData().urls():
                # Check if the suffix of the files are actual images
                file = QFileInfo(r.url())
                if file.suffix() not in ACCEPTABLE_FILES:
                    onlyImgs = False
                    break
                # Add file path if link was usable
                links.append(file.absoluteFilePath())

            if onlyImgs:
                self.filesRecieved.emit(links)
                self.swap.emit(View.Load)
        else:
            event.ignore()
