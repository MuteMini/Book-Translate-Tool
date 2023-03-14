from views import View, ViewWidget
from imaging import LoadWidget, WorkerResult, ImageModel

from PyQt6.QtCore import (
    Qt, pyqtSignal, QFileInfo, QRect, QPoint, QSize
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QMenu, QFileDialog, QStyle, QMainWindow,
    QScrollArea, QGroupBox, 
    QLayout, QLayoutItem, QGridLayout, QVBoxLayout, QHBoxLayout, QStackedLayout
)
from PyQt6.QtGui import (
    QDragMoveEvent, QAction, QImage, QPixmap
)

ACCEPTABLE_FILES = ['png', 'jpg', 'jpeg']

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Book Text Remover")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(800, 600)

        # All scenes being initialized
        self.upload_widget      = UploadWidget()
        self.load_widget        = LoadWidget()
        self.result_widget      = ResultWidget()
        self.crop_widget        = EditCropWidget()
        self.mask_widget        = EditMaskWidget()

        self.upload_widget.swap.connect(self._set_view)
        self.load_widget.swap.connect(self._set_view)
        self.result_widget.swap.connect(self._set_view)
        self.crop_widget.swap.connect(self._set_view)
        self.mask_widget.swap.connect(self._set_view)

        self.upload_widget.files_ready.connect(self.load_widget.recieve_files)
        self.load_widget.result_ready.connect(self.result_widget.recieve_result)
        
        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.upload_widget)
        self.stack_layout.addWidget(self.load_widget)
        self.stack_layout.addWidget(self.result_widget)
        self.stack_layout.addWidget(self.crop_widget)
        self.stack_layout.addWidget(self.mask_widget)

        container = QWidget()
        container.setLayout(self.stack_layout)

        self.setCentralWidget(container)

    def _set_view(self, v):
        match v:
            case View.UPLOAD:
                self.stack_layout.setCurrentWidget(self.upload_widget)
            case View.LOAD:
                self.stack_layout.setCurrentWidget(self.load_widget)
            case View.RESULT:
                self.stack_layout.setCurrentWidget(self.result_widget)
            case View.EDIT_CROP:
                self.stack_layout.setCurrentWidget(self.crop_widget)
            case View.EDIT_MASK:
                self.stack_layout.setCurrentWidget(self.mask_widget)

class UploadWidget(QWidget, ViewWidget):
    files_ready = pyqtSignal(list)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.setAcceptDrops(True)

        self._button = QPushButton()
        self._button.setText("Add Files")
        self._button.clicked.connect(self._get_file)

        self._upload_icon = QLabel()
        file_dialog = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart)
        self._upload_icon.setPixmap(file_dialog.pixmap(50, 50))
        self._upload_icon.setGeometry(50, 50, 50, 50)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self._button)

        grid_layout = QGridLayout(self)
        grid_layout.addWidget(self._upload_icon, 0, 0, Qt.AlignmentFlag.AlignHCenter)
        grid_layout.addLayout(button_layout, 1, 0)

    def _get_file(self):
        file_name = QFileDialog.getOpenFileNames(self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
        if len(file_name[0]) == 0:
            return
        self.files_ready.emit(file_name[0])
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

    def dropEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()

            # Parse all the files and make sure there are only images.
            links = []
            if e.mimeData().urls() is None:
                return
            for r in e.mimeData().urls():
                file = QFileInfo(r.toLocalFile())
                if file.suffix() not in ACCEPTABLE_FILES:
                    return
                links.append(file.absoluteFilePath())

            self.files_ready.emit(links)
            self.swap.emit(View.LOAD)
        else:
            e.ignore()

# This layout comes from https://doc.qt.io/archives/qt-4.8/qt-layouts-flowlayout-example.html
# The python version comes from https://stackoverflow.com/questions/41621354/pyqt-wrap-around-layout-of-widgets-inside-a-qscrollarea
# Allows for horizontal layout of pages until it needs to wrap over vertically.
class PagesLayout(QLayout):
    def __init__(self, parent=None, margin=10, hspacing=5, vspacing=5):
        super(PagesLayout, self).__init__(parent)

        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        del self._items[:]

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def horizontalSpacing(self):
        return self._hspacing

    def verticalSpacing(self):
        return self._vspacing

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width: int):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super(PagesLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        item: QLayoutItem
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(),
                      2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect: QRect, test: bool):
        l, t, r, b = self.getContentsMargins()
        effective = rect.adjusted(+l, +t, -r, -b)
        x = effective.x()
        y = effective.y()
        line_height = 0

        # The essential code that wraps the items in this layout vertically
        item: QLayoutItem
        for item in self._items:
            next_x = x + item.sizeHint().width()
            if next_x > rect.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._vspacing
                next_x = x + item.sizeHint().width()
                line_height = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x + self._hspacing
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - effective.y()

class PagesWidget(QLabel):
    clicked = pyqtSignal(ImageModel)

    def __init__(self, model: ImageModel = None, display = False):
        super(QWidget, self).__init__(None)

        self.setMinimumSize(100, 141)

        self.menu = QMenu(self)

        if not display:
            self.setMaximumSize(100, 141)
            self.menu.addAction(QAction("Save as Image", self))
            self.menu.addAction(QAction("Delete", self))

        self.model = model
        self.image = None
        if self.model is not None:
            self.model.content_changed.connect(self.update_contents)
            self.update_contents()

    def update_contents(self):
        h, w, ch = self.model.final.shape
        self.image = QPixmap.fromImage(QImage(self.model.final, w, h, ch*w, QImage.Format.Format_BGR888))
        self.resizeEvent(None)

    def contextMenuEvent(self, e):
        self.menu.exec(e.globalPos())

    def mousePressEvent(self, e):
        self.clicked.emit(self.model)

    def resizeEvent(self, e):
        if self.image is not None:
            self.setPixmap(self.image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

class ResultWidget(QWidget, ViewWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self._sel_page = PagesWidget(display = True)
        self._pages_layout = PagesLayout()

        pages = QWidget()
        pages.setLayout(self._pages_layout)

        scroll_widget = QScrollArea()
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(pages)

        crop_button = QPushButton("Recrop")
        mask_button = QPushButton("Remask")

        button_layout = QHBoxLayout()
        button_layout.addWidget(crop_button)
        button_layout.addSpacing(1)
        button_layout.addWidget(mask_button)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(self._sel_page, Qt.AlignmentFlag.AlignCenter)
        left_layout.addSpacing(1)
        left_layout.addLayout(button_layout)
        
        left_group = QGroupBox("Selected Page")
        left_group.setLayout(left_layout)
        
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(left_group, 1)
        main_layout.addWidget(scroll_widget, 2)

    def recieve_result(self, r: WorkerResult):
        if r.type == 'inputs':
            for model in r.result:
                page = PagesWidget(model)
                self._pages_layout.addWidget(page)
                page.clicked.connect(self.set_viewing_page)
        pass

    def set_viewing_page(self, model: ImageModel):
        self._sel_page.model = model
        self._sel_page.update_contents()

class EditCropWidget(QWidget, ViewWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

class EditMaskWidget(QWidget, ViewWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)