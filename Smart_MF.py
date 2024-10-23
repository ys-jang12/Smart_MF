import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QDesktopWidget, QMainWindow, QAction, QGridLayout, QHBoxLayout, QGroupBox
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt
from picamera2 import Picamera2
import cv2
import requests
import json
import base64
import uuid
import time

from pydub import AudioSegment
AudioSegment.converter = "/usr/bin/ffmpeg"

api_url = "https://1pfzoy3rip.apigw.ntruss.com/custom/v1/29106/232a126588edab4a02c8244f2b2907a3ac5c77cdba5b1232f150b482b77c13bc/general"
secret_key = "bXFBZ3ZKZk9aV0pYQlR5VGVlaURqcUpFWVFGWUptdkI="

def run_clova_ocr(image_path):
    request_json = {
        'images': [
            {
                'format': 'jpg',
                'name': 'demo'
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(round(time.time() * 1000))
    }

    headers = {
        'X-OCR-SECRET': secret_key
    }

    with open(image_path, 'rb') as file:
        files = {'file': file}

        response = requests.post(api_url, headers=headers, data={'message': json.dumps(request_json)}, files=files)
        if response.status_code == 200:
            result = response.json()
            ocr_result_path = image_path.replace('.jpg', '_ocr_result.txt')
            with open(ocr_result_path, 'w', encoding='utf-8') as text_file:
                json.dump(result, text_file, indent=2, ensure_ascii=False)

            text = ""
            all_texts = []
            if 'images' in result and len(result['images']) > 0 and 'fields' in result['images'][0]:
                for field in result['images'][0]['fields']:
                    text = field['inferText']
                    all_texts.append(text)

            full_text = ' '.join(all_texts)
            with open(image_path.replace('.jpg', '_captured_text.txt'), 'w', encoding='utf-8') as text_file:
                text_file.write(full_text)
            return full_text
        else:
             print("Error:", response.status_code, response.text)

class CameraApp(QWidget):
    def read_text_from_latest_capture(self):
        import glob
        import os
        import gtts
        from pydub import AudioSegment
        from pydub.playback import play
        
        list_of_files = glob.glob('capture_img/captured_frame_*_captured_text.txt')
        if list_of_files:
            latest_file = max(list_of_files, key=os.path.getmtime)
            with open(latest_file, 'r', encoding='utf-8') as file:
                text = file.read()
                print(text)
                tts = gtts.gTTS(text, lang='ko')
                audio_file = latest_file.replace('.txt', '.mp3')
                tts.save(audio_file)
                sound = AudioSegment.from_mp3(audio_file)
                play(sound)
    def run_ocr_on_last_capture(self):
        import glob
        list_of_files = glob.glob('capture_img/captured_frame_*.jpg')
        if list_of_files:
            import os
            latest_file = max(list_of_files, key=os.path.getmtime)
            full_text = run_clova_ocr(latest_file)
            print(full_text)
        self.read_text_button.setEnabled(True)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Viewer")
        self.setGeometry(100, 85, 800, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.center()

        self.main_layout = QGridLayout()

        self.camera_group = QGroupBox("Camera Feed")
        self.camera_layout = QVBoxLayout()
        self.label = QLabel()
        self.label.setFixedSize(608, 342)
        self.label.setScaledContents(True)
        self.camera_layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.camera_group.setLayout(self.camera_layout)
        self.main_layout.addWidget(self.camera_group, 0, 0, alignment=Qt.AlignCenter)

        self.buttons_group = QGroupBox()
        self.buttons_layout = QVBoxLayout()

        self.capture_button = QPushButton("Capture Camera")
        self.capture_button.setFixedSize(100, 70)
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self.capture_frame_without_ocr)
        self.buttons_layout.addWidget(self.capture_button)

        self.ocr_button = QPushButton("Run OCR")
        self.ocr_button.setFixedSize(100, 70)
        self.ocr_button.setEnabled(False)
        self.ocr_button.clicked.connect(self.run_ocr_on_last_capture)
        self.buttons_layout.addWidget(self.ocr_button)

        self.read_text_button = QPushButton("Read Text")
        self.read_text_button.setFixedSize(100, 70)
        self.read_text_button.setEnabled(False)
        self.read_text_button.clicked.connect(self.read_text_from_latest_capture)
        self.buttons_layout.addWidget(self.read_text_button)

        self.toggle_button = QPushButton("Camera On/Off")
        self.toggle_button.setFixedSize(100, 70)
        self.toggle_button.clicked.connect(self.toggle_camera)
        self.buttons_layout.addWidget(self.toggle_button)

        self.close_button = QPushButton("Close")
        self.close_button.setFixedSize(100, 70)
        self.close_button.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_button)

        self.buttons_group.setLayout(self.buttons_layout)
        self.main_layout.addWidget(self.buttons_group, 0, 1, alignment=Qt.AlignRight)

        self.setLayout(self.main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.picam2 = Picamera2()
        camera_config = self.picam2.create_still_configuration(main={'size': (1920, 1080)})
        self.picam2.configure(camera_config)
        self.frame = None

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.left(), qr.top() - 15)

    def toggle_camera(self):
        if self.timer.isActive():
            self.timer.stop()
            self.picam2.stop()
            self.label.clear()
            self.capture_button.setEnabled(False)
        else:
            self.picam2.start()
            self.timer.start(20)
            self.capture_button.setEnabled(True)

    def capture_frame_without_ocr(self):
        if not self.timer.isActive():
            print("Camera is not active. Please turn on the camera before capturing.")
            return
        if self.frame is not None:
            import os
        capture_dir = 'capture_img'
        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir)
        file_path = os.path.join(capture_dir, f"captured_frame_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
        cv2.imwrite(file_path, self.frame)
        self.ocr_button.setEnabled(True)
            

    def update_frame(self):
        self.frame = self.picam2.capture_array()
        if self.frame is not None:
            frame_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame_rgb, frame_rgb.shape[1], frame_rgb.shape[0], QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            self.label.setPixmap(pixmap)
            self.label.setScaledContents(True)

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
            self.picam2.stop()
        event.accept()

class LibraryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Library Viewer")
        self.setGeometry(100, 85, 800, 450)
        self.center()

        self.layout = QVBoxLayout()
        self.label = QLabel("Library Content")
        self.layout.addWidget(self.label, alignment=Qt.AlignCenter)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)

        self.setLayout(self.layout)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.left(), qr.top() - 15)

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Menu")
        self.setGeometry(100, 10, 800, 450)
        self.center()

        self.layout = QGridLayout()
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_widget.setLayout(self.layout)

        self.image_label = QLabel()
        self.image_label.setPixmap(QPixmap(200, 200))
        self.image_label.setText("Image Here")
        self.layout.addWidget(self.image_label, 0, 0, alignment=Qt.AlignLeft | Qt.AlignTop)

        self.camera_button = QPushButton("Open Camera")
        self.camera_button.setFixedSize(100, 100)
        self.layout.addWidget(self.camera_button, 0, 1, alignment=Qt.AlignTop | Qt.AlignRight)
        self.camera_button.clicked.connect(self.open_camera)

        self.library_button = QPushButton("Open Library")
        self.library_button.setFixedSize(100, 50)
        self.layout.addWidget(self.library_button, 1, 1, alignment=Qt.AlignTop | Qt.AlignRight)
        self.library_button.clicked.connect(self.open_library)

        self.close_button = QPushButton("Exit")
        self.close_button.setFixedSize(100, 50)
        self.layout.addWidget(self.close_button, 2, 1, alignment=Qt.AlignBottom | Qt.AlignRight)
        self.close_button.clicked.connect(self.close)

        self.camera_app = None
        self.library_app = None

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.left(), qr.top() - 15)

    def open_camera(self):
        if self.camera_app is None:
            self.camera_app = CameraApp()
        self.camera_app.show()

    def open_library(self):
        if self.library_app is None:
            self.library_app = LibraryApp()
        self.library_app.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Macintosh")
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())
