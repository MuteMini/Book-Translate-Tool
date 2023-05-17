from views import View, ViewWidget
from detection import DocUtils
import constants

import traceback

from keras_ocr.pipeline import Pipeline
from keras import backend as K

from PIL import Image

from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QObject,
    QThreadPool, QRunnable, QMutex, QMutexLocker
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QMessageBox,
)   
from PyQt6.QtGui import QImage, QPixmap

# Worker Class comes from this repo: https://github.com/mochisue/pyqt-async-sample/blob/7bd6124c3c6fa8e88f792581dbfda44d7144552b/src/sample.py#L144
# Allows for any function to be run using the QThreadPool, works perfectly for our use case of QT's asynchronous features.
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(str, int, int)

# Any function going in here should be able to take the worker object.
class Worker(QRunnable):
    def __init__(self, fn_run, *args, **kwargs):
        super().__init__()
        self.fn_run = fn_run
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.mutex = QMutex()
        self.is_stop = False

    @pyqtSlot()
    def run(self):
        result = None
        try:
            with QMutexLocker(self.mutex):
                self.is_stop = False
            result = self.fn_run(self, *self.args, **self.kwargs)
        except:
            self.signals.error.emit(traceback.format_exc())
        else:
            self.signals.finished.emit()
        finally:
            if result is not None:
                self.signals.result.emit(result)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.is_stop = True

class ImageModel(QObject):
    content_changed = pyqtSignal()

    def __init__(self, orig, corner, mask, final, parent=None):
        super().__init__(parent)
        self.orig = orig
        self.corner = corner
        self.tx_mask = mask

        h, w, ch = orig.shape
        self.orig_pix = QPixmap.fromImage(QImage(orig, w, h, ch*w, QImage.Format.Format_BGR888))

        self.update_final_pix(final)

    def update_final_pix(self, final):
        h, w, ch = final.shape
        self.final_pix = QPixmap.fromImage(QImage(final, w, h, ch*w, QImage.Format.Format_BGR888))

### ------------------------------------------------------------------------------ ###

class LoadWidget(QWidget, ViewWidget):
    result_ready = pyqtSignal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(1) 

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setFixedWidth(350)
        self._progress_bar.setValue(0)

        self._label = QLabel()
        self._label.resize(300, 20)

        self.worker = None
        self.pipeline = Pipeline()
        
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self._progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        layout.setContentsMargins(50,20,50,20)
        
        self.setLayout(layout)
    
    def stop_worker(self):
        if isinstance(self.worker, Worker):
            self.worker.stop()

    # Replace test thread with full thread
    @pyqtSlot(list)
    def recieve_files(self, img_paths):
        self.start_thread(Worker(self._run_full_thread, img_paths))

    @pyqtSlot(ImageModel)
    def recrop_model(self, model):
        self.start_thread(Worker(self._run_recrop_thread, model))

    @pyqtSlot(list, str, str)
    def save_files(self, img, path, type):
        self.start_thread(Worker(self._run_save_thread, img, path, type))

    def start_thread(self, worker: Worker):
        worker.signals.error.connect(self._error_thread)
        worker.signals.result.connect(self._result_thread)
        worker.signals.finished.connect(self._finish_thread)
        worker.signals.progress.connect(self._progress_thread)
        self._thread_pool.start(worker)
        self.worker = worker

    def _error_thread(self, message):
        print(message)

    def _result_thread(self, result):
        self.worker = None
        
        match result[0]:
            case 'final':
                QMessageBox.about(self, "Alert", "File Saved!")
                self.swap.emit(View.UPLOAD)
            case 'singlesave':
                QMessageBox.about(self, "Alert", "Image Saved!")
                self.swap.emit(View.RESULT)
            case _:
                self.result_ready.emit(result)
                self.swap.emit(View.RESULT)

    def _finish_thread(self):
        self._thread_pool.waitForDone()

    def _progress_thread(self, text, progress, limit):
        self._label.setText(text)
        self._progress_bar.setRange(0, limit)
        self._progress_bar.setValue(progress)

    def _run_full_thread(self, worker_object: Worker, img_paths):
        worker_object.signals.progress.emit(f"Starting Process", 0, 0)

        sorted(img_paths)

        progress = 0
        limit = len(img_paths)*2

        crops = []
        result = []
        for id, img in enumerate(img_paths):
            worker_object.signals.progress.emit(f"Cropping Image #{id+1}", progress, limit)
            if worker_object.is_stop:
                return None
            
            orig, corner = DocUtils.find_document(img)
            crop = DocUtils.crop_document(orig, corner)
            progress += 1

            crops.append((orig, corner, crop))

        for id, (orig, corner, crop) in enumerate(crops):
            worker_object.signals.progress.emit(f"Removing Text #{id+1}", progress, limit)
            if worker_object.is_stop:
                return None

            mask = DocUtils.text_mask(crop, self.pipeline)
            final = DocUtils.resized_final(crop, mask, height=600)
            progress += 1

            if worker_object.is_stop:
                return None
            
            result.append(ImageModel(orig, corner, mask, final))
            
        worker_object.signals.progress.emit("Wrapping up", 1, 1)
        K.clear_session()
        return 'inputs', result
    
    def _run_recrop_thread(self, worker_object: Worker, model: ImageModel):
        worker_object.signals.progress.emit(f"Starting Process", 0, 0)

        worker_object.signals.progress.emit(f"Cropping Image", 0, 2)
        if worker_object.is_stop:   
            return None
        crop = DocUtils.crop_document(model.orig, model.corner)

        worker_object.signals.progress.emit(f"Removing Text", 1, 2)
        if worker_object.is_stop:
            return None
        model.tx_mask = DocUtils.text_mask(crop, self.pipeline)
        model.update_final_pix(DocUtils.resized_final(crop, model.tx_mask, height=600))

        worker_object.signals.progress.emit("Wrapping up", 1, 1)
        K.clear_session()
        return 'recrop', model
    
    def _run_save_thread(self, worker_object: Worker, imgs, path, type):
        worker_object.signals.progress.emit(f"Saving as File", 0, 0)

        progress = 0
        limit = len(imgs)

        pil_img: list[Image.Image] = []
        for id, model in enumerate(imgs):
            worker_object.signals.progress.emit(f"Appending Page {id}", progress, limit)
            if worker_object.is_stop:
                return None
            
            crop = DocUtils.crop_document(model.orig, model.corner)
            final = DocUtils.resized_final(crop, model.tx_mask, width=constants.SAVE_WIDTH)
            pil_img.append(DocUtils.opencv_to_pil(final))
            progress += 1

        # Could be reused to save as multiple different types
        pil_img[0].save(path, type, resolution=100.0, save_all=True, append_images=pil_img[1:])

        worker_object.signals.progress.emit("Done", 1, 1)
        return 'final' if type == "PDF" else "singlesave", None