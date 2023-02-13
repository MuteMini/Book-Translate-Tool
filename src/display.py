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
    files_recieved = pyqtSignal(list)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self._button = QPushButton()
        self._button.setText("Add Files")
        self._button.clicked.connect(self._get_file)

        self._upload_icon = QLabel()
        file_dialog = self.style().standardIcon( QStyle.StandardPixmap.SP_FileDialogStart )
        self._upload_icon.setPixmap(file_dialog.pixmap(50, 50))
        self._upload_icon.setGeometry(50, 50, 50, 50)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self._button)

        grid_layout = QGridLayout()
        grid_layout.addWidget(self._upload_icon, 0, 0, Qt.AlignmentFlag.AlignHCenter)
        grid_layout.addLayout(button_layout, 1, 0)
        self.setLayout(grid_layout)

    def _get_file(self):
        file_name = QFileDialog.getOpenFileNames(self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
        self.files_recieved.emit(file_name[0])
        self.swap.emit(View.LOAD)

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
            only_imgs = True

            for r in event.mimeData().urls():
                # Check if the suffix of the files are actual images
                file = QFileInfo(r.url())
                if file.suffix() not in ACCEPTABLE_FILES:
                    only_imgs = False
                    break
                # Add file path if link was usable
                links.append(file.absoluteFilePath())

            if only_imgs:
                self.files_recieved.emit(links)
                self.swap.emit(View.LOAD)
        else:
            event.ignore()
