from views import View, ViewWidget

from PyQt6.QtCore import (
    Qt, pyqtSignal, QFileInfo, QRect, QPoint, QSize
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QMenu, QFileDialog, QStyle,
    QScrollArea, QGroupBox,
    QLayout, QLayoutItem, QGridLayout, QVBoxLayout, QHBoxLayout,
)
from PyQt6.QtGui import (
    QDragMoveEvent, QAction,
    QColor, QPalette,
)

ACCEPTABLE_FILES = ['png', 'jpg', 'jpeg']


class UploadWidget(QWidget, ViewWidget):
    files_recieved = pyqtSignal(list)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.setAcceptDrops(True)

        self._button = QPushButton()
        self._button.setText("Add Files")
        self._button.clicked.connect(self._get_file)

        self._upload_icon = QLabel()
        file_dialog = self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogStart)
        self._upload_icon.setPixmap(file_dialog.pixmap(50, 50))
        self._upload_icon.setGeometry(50, 50, 50, 50)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self._button)

        grid_layout = QGridLayout()
        grid_layout.addWidget(self._upload_icon, 0, 0,
                              Qt.AlignmentFlag.AlignHCenter)
        grid_layout.addLayout(button_layout, 1, 0)
        self.setLayout(grid_layout)

    def _get_file(self):
        file_name = QFileDialog.getOpenFileNames(
            self, "Open file", 'c:\\', "Image files (*.jpg *.png)")
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

    def dropEvent(self, e: QDragMoveEvent):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()

            # Parse all the files and make sure there are only images.
            links = []
            for r in e.mimeData().urls():
                file = QFileInfo(r.url())
                if file.suffix() not in ACCEPTABLE_FILES:
                    return
                links.append(file.absoluteFilePath())

            self.files_recieved.emit(links)
            self.swap.emit(View.LOAD)
        else:
            e.ignore()

# This layout comes from https://doc.qt.io/archives/qt-4.8/qt-layouts-flowlayout-example.html
# The python version of this layout comes from https://stackoverflow.com/questions/41621354/pyqt-wrap-around-layout-of-widgets-inside-a-qscrollarea
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


class PagesWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # Test code, setting pages widget to a set size with a color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('red'))
        self.setPalette(palette)

        self.setMinimumSize(100, 141)

        self.menu = QMenu(self)
        self.menu.addAction(QAction("Save as Image", self))
        self.menu.addAction(QAction("Delete", self))

    def contextMenuEvent(self, e):
        self.menu.exec(e.globalPos())


class ResultWidget(QWidget, ViewWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # self._pages =
        # self._sel_page = 

        pages_layout = PagesLayout()
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())
        pages_layout.addWidget(PagesWidget())

        group = QGroupBox("Processed Pages")
        group.setLayout(pages_layout)

        scroll_widget = QScrollArea()
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setWidget(group)

        leftLayout = QVBoxLayout()
        
        main_layout = QHBoxLayout()
        main_layout.addLayout(leftLayout, 1)
        main_layout.addWidget(scroll_widget, 2)

        self.setLayout(main_layout)
