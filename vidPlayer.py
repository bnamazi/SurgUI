from PyQt5.QtWidgets import QApplication, QWidget, QAction, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, \
    QSlider, QStyle, QSizePolicy, QFileDialog, QLineEdit, QFormLayout, QGroupBox, QScrollArea, QMainWindow
import sys
import os
import platform
import cv2
import vlc
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QVideoFrame, QAbstractVideoSurface, QAbstractVideoBuffer, \
    QVideoSurfaceFormat
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QPalette, QImage, QPainter, QFont
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QPoint, QRect, QObject
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets
from functools import partial


class VideoFrameGrabber(QAbstractVideoSurface):
    frameAvailable = pyqtSignal(QImage)

    def __init__(self, widget: QWidget, parent: QObject):
        super().__init__(parent)

        self.widget = widget

    def supportedPixelFormats(self, handleType):
        return [QVideoFrame.Format_ARGB32, QVideoFrame.Format_ARGB32_Premultiplied,
                QVideoFrame.Format_RGB32, QVideoFrame.Format_RGB24, QVideoFrame.Format_RGB565,
                QVideoFrame.Format_RGB555, QVideoFrame.Format_ARGB8565_Premultiplied,
                QVideoFrame.Format_BGRA32, QVideoFrame.Format_BGRA32_Premultiplied, QVideoFrame.Format_BGR32,
                QVideoFrame.Format_BGR24, QVideoFrame.Format_BGR565, QVideoFrame.Format_BGR555,
                QVideoFrame.Format_BGRA5658_Premultiplied, QVideoFrame.Format_AYUV444,
                QVideoFrame.Format_AYUV444_Premultiplied, QVideoFrame.Format_YUV444,
                QVideoFrame.Format_YUV420P, QVideoFrame.Format_YV12, QVideoFrame.Format_UYVY,
                QVideoFrame.Format_YUYV, QVideoFrame.Format_NV12, QVideoFrame.Format_NV21,
                QVideoFrame.Format_IMC1, QVideoFrame.Format_IMC2, QVideoFrame.Format_IMC3,
                QVideoFrame.Format_IMC4, QVideoFrame.Format_Y8, QVideoFrame.Format_Y16,
                QVideoFrame.Format_Jpeg, QVideoFrame.Format_CameraRaw, QVideoFrame.Format_AdobeDng]

    def isFormatSupported(self, format):
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(format.pixelFormat())
        size = format.frameSize()

        return imageFormat != QImage.Format_Invalid and not size.isEmpty() and \
               format.handleType() == QAbstractVideoBuffer.NoHandle

    def start(self, format: QVideoSurfaceFormat):
        imageFormat = QVideoFrame.imageFormatFromPixelFormat(format.pixelFormat())
        size = format.frameSize()

        if imageFormat != QImage.Format_Invalid and not size.isEmpty():
            self.imageFormat = imageFormat
            self.imageSize = size
            self.sourceRect = format.viewport()

            super().start(format)

            self.widget.updateGeometry()
            self.updateVideoRect()

            return True
        else:
            return False

    def stop(self):
        self.currentFrame = QVideoFrame()
        self.targetRect = QRect()

        super().stop()

        self.widget.update()

    def present(self, frame):
        if frame.isValid():
            cloneFrame = QVideoFrame(frame)
            cloneFrame.map(QAbstractVideoBuffer.ReadOnly)
            image = QImage(cloneFrame.bits(), cloneFrame.width(), cloneFrame.height(),
                           QVideoFrame.imageFormatFromPixelFormat(cloneFrame.pixelFormat()))
            self.frameAvailable.emit(image)  # this is very important
            cloneFrame.unmap()

        if self.surfaceFormat().pixelFormat() != frame.pixelFormat() or \
                self.surfaceFormat().frameSize() != frame.size():
            self.setError(QAbstractVideoSurface.IncorrectFormatError)
            self.stop()

            return False
        else:
            self.currentFrame = frame
            self.widget.repaint(self.targetRect)

            return True

    def updateVideoRect(self):
        size = self.surfaceFormat().sizeHint()
        size.scale(self.widget.size().boundedTo(size), Qt.KeepAspectRatio)

        self.targetRect = QRect(QPoint(0, 0), size)
        self.targetRect.moveCenter(self.widget.rect().center())

    def paint(self, painter):
        if self.currentFrame.map(QAbstractVideoBuffer.ReadOnly):
            oldTransform = self.painter.transform()

        if self.surfaceFormat().scanLineDirection() == QVideoSurfaceFormat.BottomToTop:
            self.painter.scale(1, -1)
            self.painter.translate(0, -self.widget.height())

        image = QImage(self.currentFrame.bits(), self.currentFrame.width(), self.currentFrame.height(),
                       self.currentFrame.bytesPerLine(), self.imageFormat)

        self.painter.drawImage(self.targetRect, image, self.sourceRect)

        self.painter.setTransform(oldTransform)

        self.currentFrame.unmap()


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Surgical Video Player")
        self.setGeometry(350, 100, 700, 500)
        self.setWindowIcon(QIcon('player.png'))

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        self.setFocusPolicy(Qt.StrongFocus)

        self.num_panels = 0

        self.is_paused = False

        self.init_ui()

        self.showMaximized()

    def init_ui(self):
        # create the directory where the outputs for all videos are saved
        if not os.path.exists('outputs'):
            os.mkdir('outputs')

        self.instance = vlc.Instance()
        self.media = None
        # create media player object
        self.mediaPlayer = self.instance.media_player_new()  # QMediaPlayer(None, QMediaPlayer.VideoSurface)

        # In this widget, the video will be drawn
        if platform.system() == "Darwin":  # for MacOS
            self.videowidget = QtWidgets.QMacCocoaViewContainer(0)
        elif platform.system() == "Windows":
            self.videowidget = QtWidgets.QFrame()
        else:
            self.videowidget = QtWidgets.QMacCocoaViewContainer(0)
        # create videowidget object
        # self.videowidget = QVideoWidget()
        self.videowidget_g = QVideoWidget()

        # create open button
        openBtn = QPushButton('Open Video')
        openBtn.clicked.connect(self.open_video)

        # create button for taking a snapshot
        snapBtn = QPushButton('snapshot (save the image)')
        snapBtn.clicked.connect(self.screenshotCall)
        # snapBtn.setEnabled(True)
        self.ImagesBuffer = None

        # create button for playing
        self.playBtn = QPushButton()
        self.playBtn.setEnabled(False)
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.play_video)

        self.twoxBtn = QPushButton('2X')
        self.twoxBtn.setEnabled(True)
        self.twoxBtn.setFixedWidth(30)

        # create slider
        self.slider = QSlider(Qt.Horizontal)
        #self.slider.setRange(0, 0)
        #self.slider.setSingleStep(5000)
        self.slider.setMaximum(100000)
        self.slider.sliderMoved.connect(self.position_changed)
        # self.slider.valueChanged.connect(self.set_position)
        self.slider.sliderPressed.connect(self.position_changed)

        # create LCD for displaying the position of the slider
        # self.lcd = QLCDNumber(self)
        self.l = QLabel('0:00:00')
        self.l.setStyleSheet('color: white')
        self.slider.valueChanged.connect(self.display_time)  # (self.lcd.display)
        self.d =QLabel('0:00:00')
        self.d.setStyleSheet('color: white')


        # create label
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # create hbox layout
        hboxLayout = QHBoxLayout()
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        # set widgets to the hbox layout
        # hboxLayout.addWidget(openBtn)
        hboxLayout.addWidget(self.playBtn)
        hboxLayout.addWidget(self.l)
        hboxLayout.addWidget(self.slider)
        hboxLayout.addWidget(self.d)
        hboxLayout.addWidget(self.playBtn)

        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(snapBtn)

        # create vbox layout
        vboxLayout = QVBoxLayout()
        # set widgets to the vbox layout
        # vboxLayout.addWidget(openBtn)
        vboxLayout.addWidget(self.videowidget)
        vboxLayout.addLayout(hboxLayout)
        vboxLayout.addLayout(bottomLayout)
        vboxLayout.addWidget(self.label)

        self.mainLayout = QHBoxLayout()
        self.mainLayout.addLayout(vboxLayout)

        # create empty lists for the panels to be added
        self.groupbox = [None] * 10
        self.formLayout = [None] * 10
        self.form_title = [None] * 10
        self.panelRemoveBtn = [None] * 10
        self.scroll = [None] * 10
        self.tasklist = [None] * 10
        self.startingButtonlist = [None] * 10
        self.startingTimelist = [None] * 10
        self.endingButtonlist = [None] * 10
        self.endingTimelist = [None] * 10
        self.saveEntryBtn = [None] * 10
        self.clearEntryBtn = [None] * 10

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)

        self.setLayout(self.mainLayout)

        # create menu bar
        menuBar = QMenuBar(self)
        # menuBar.setStyleSheet("color: white")
        fileMenu = menuBar.addMenu('&File')
        HelpMenu = menuBar.addMenu('&Help')

        openVideoAction = QAction('&Open Video', self)
        openVideoAction.setShortcut('Ctrl+O')
        openVideoAction.setStatusTip('Open Video')
        openVideoAction.triggered.connect(self.open_video)

        addPanelAction = QAction('&Add Panel', self)
        addPanelAction.setStatusTip('Add Panel')
        addPanelAction.triggered.connect(self.add_panel)

        addPanelFileAction = QAction('&Add Panel From File', self)
        addPanelFileAction.setStatusTip('Add Panel From File')
        addPanelFileAction.triggered.connect(self.add_panel_from_file)

        saveEntriesAction = QAction('&Save', self)
        saveEntriesAction.setStatusTip('Save all entries')
        saveEntriesAction.setShortcut('Ctrl+S')
        saveEntriesAction.triggered.connect(self.save)

        clearPanelsAction = QAction('&Clear Panels', self)
        clearPanelsAction.setStatusTip('Clear all panels')
        clearPanelsAction.setShortcut('Ctrl+C')
        clearPanelsAction.triggered.connect(self.clearPanels)

        exitAction = QAction('&Exit', self )
        exitAction.setStatusTip('Exit')
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)

        # fileMenu.addAction(addPanelAction)
        fileMenu.addAction(addPanelFileAction)
        fileMenu.addAction(openVideoAction)
        fileMenu.addAction(saveEntriesAction)
        fileMenu.addAction(clearPanelsAction)
        fileMenu.addAction(exitAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.play_video()


        elif event.key() == Qt.Key_Right:
            p = self.slider.value()
            p = p + int (500000000  / self.media.get_duration() )
            self.set_position(p)

        elif event.key() == Qt.Key_Left:

            p = self.slider.value()
            p = p - int (500000000  / self.media.get_duration() )
            self.set_position(p)


        elif event.key() == Qt.Key_F5:

            self.close()
        else:

            super().keyPressEvent(event)

    def open_video(self):
        # opens video file, create the directory for the videos outputs, play the video
        filename, _ = QFileDialog.getOpenFileName(self, "Open Video")#, filter="Videos (*.Mmov, *.mp4)")

        if filename != '':
            # self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
            self.media = self.instance.media_new(filename)
            self.mediaPlayer.set_media(self.media)
            self.media.parse()
            self.setWindowTitle(self.media.get_meta(0))

            self.playBtn.setEnabled(True)

            if platform.system() == "Linux":  # for Linux using the X Server
                self.mediaPlayer.set_xwindow(int(self.videowidget.winId()))
            elif platform.system() == "Windows":  # for Windows
                self.mediaPlayer.set_hwnd(int(self.videowidget.winId()))
            else:  # if platform.system() == "Darwin":  # for MacOS
                self.mediaPlayer.set_nsobject(int(self.videowidget.winId()))

            self.cap = cv2.VideoCapture(filename)
            self.play_video()

            self.d.setText(str(self.getDurationValue()))

            directory = (os.path.basename(filename))
            self.vidname = directory
            if not os.path.exists('outputs/' + directory):
                os.mkdir('outputs/' + directory)
            self.save_directory = 'outputs/' + directory

            if not os.path.exists('outputs/' + directory + '/images'):
                os.mkdir('outputs/' + directory + '/images')
            self.image_save_directory = 'outputs/' + directory + '/images'

            # clear panels
            if self.num_panels > 0:
                self.clearPanels()


    def play_video(self):
        if self.mediaPlayer.is_playing():
            self.mediaPlayer.pause()
            self.is_paused = True
            ##self.mediaPlayer_g.pause()
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay)
            )
            self.timer.stop()


        else:
            self.mediaPlayer.play()
            ##self.mediaPlayer_g.play()
            self.timer.start()
            self.is_paused = False
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause)
            )

    def display_time(self):

        time = self.getSliderValue()
        self.l.setText( '{}'.format(str(time)))

    def add_panel(self):
        # for manually added panels
        pass

    def onpanelRemoveBtnClicked(self, panel_index):
        pass
        # self.mainLayout.removeWidget(self.scroll[panel_index]) deleteLater()

    def add_panel_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Text", filter= "Text files (*.txt)")

        if filename != '':
            title = str(os.path.basename(filename)).split('.')[0]
            with open(filename) as f:
                lines = f.read().splitlines()
            print('opened panel', title)

            self.num_panels += 1

            self.panel_index = self.num_panels

            self.tasklist[self.panel_index] = []
            self.startingButtonlist[self.panel_index] = []
            self.startingTimelist[self.panel_index] = []
            self.endingButtonlist[self.panel_index] = []
            self.endingTimelist[self.panel_index] = []
            self.saveEntryBtn[self.panel_index] = []
            self.clearEntryBtn[self.panel_index] = []

            self.groupbox[self.panel_index] = QGroupBox()
            self.formLayout[self.panel_index] = QFormLayout()

            self.form_title[self.panel_index] = QLabel(title)
            self.form_title[self.panel_index].setStyleSheet('color: white')
            self.form_title[self.panel_index].setAlignment(Qt.AlignCenter)
            self.form_title[self.panel_index].setFont(QFont("Times", 12, weight=QFont.Bold))
            self.panelRemoveBtn[self.panel_index] = QPushButton('Exit')
            self.panelRemoveBtn[self.panel_index].clicked.connect(partial(self.onpanelRemoveBtnClicked, self.panel_index))

            self.formLayout[self.panel_index].addRow(
                self.form_title[self.panel_index])  # , self.panelRemoveBtn[self.panel_index])

            for i, line in enumerate(lines):
                line = line.split('#')

                self.tasklist[self.panel_index].append(QLabel(line[0]))
                self.tasklist[self.panel_index][i].setStyleSheet('background-color: black ; color: white')
                self.tasklist[self.panel_index][i].setFont(QFont("Times", 10, weight=QFont.Bold))
                self.tasklist[self.panel_index][i].setWordWrap(True)
                self.startingButtonlist[self.panel_index].append(QPushButton('starts'))
                self.startingButtonlist[self.panel_index][i].setFixedWidth(50)
                self.startingTimelist[self.panel_index].append(QLabel('0'))
                self.startingTimelist[self.panel_index][i].setStyleSheet('color: white')
                self.startingButtonlist[self.panel_index][i].clicked.connect(
                    partial(self.onstartbuttonClicked, self.panel_index, i))
                self.endingButtonlist[self.panel_index].append(QPushButton('ends'))
                self.endingButtonlist[self.panel_index][i].setFixedWidth(50)
                self.endingTimelist[self.panel_index].append(QLabel('0'))
                self.endingTimelist[self.panel_index][i].setStyleSheet('color: white')
                self.endingButtonlist[self.panel_index][i].clicked.connect(
                    partial(self.onendbuttonClicked, self.panel_index, i))
                if len(line) == 3:
                    self.startingButtonlist[self.panel_index][i].setToolTip(line[1])
                    self.endingButtonlist[self.panel_index][i].setToolTip(line[2])
                self.saveEntryBtn[self.panel_index].append(QPushButton('save'))
                self.clearEntryBtn[self.panel_index].append(QPushButton('clear'))
                self.saveEntryBtn[self.panel_index][i].setFixedWidth(50)
                self.clearEntryBtn[self.panel_index][i].setFixedWidth(50)
                self.saveEntryBtn[self.panel_index][i].setEnabled(False)
                self.saveEntryBtn[self.panel_index][i].clicked.connect(
                    partial(self.onsaveEntryBtnClicked, self.panel_index, i))
                self.clearEntryBtn[self.panel_index][i].setEnabled(False)
                self.clearEntryBtn[self.panel_index][i].clicked.connect(
                    partial(self.onclearEntryBtnClicked, self.panel_index, i))

                self.formLayout[self.panel_index].addRow(self.tasklist[self.panel_index][i])
                self.formLayout[self.panel_index].addRow(self.startingButtonlist[self.panel_index][i],
                                                         self.startingTimelist[self.panel_index][i])
                self.formLayout[self.panel_index].addRow(self.endingButtonlist[self.panel_index][i],
                                                         self.endingTimelist[self.panel_index][i])
                self.formLayout[self.panel_index].addRow(self.saveEntryBtn[self.panel_index][i],
                                                         self.clearEntryBtn[self.panel_index][i])

            self.groupbox[self.panel_index].setLayout(self.formLayout[self.panel_index])
            self.scroll[self.panel_index] = QScrollArea()
            self.scroll[self.panel_index].setWidget(self.groupbox[self.panel_index])
            self.scroll[self.panel_index].setWidgetResizable(True)
            self.scroll[self.panel_index].setFixedWidth(150)
            self.scroll[self.panel_index].setFocusPolicy(Qt.StrongFocus)
            self.mainLayout.addWidget(self.scroll[self.panel_index])

    def position_changed(self):
        self.timer.stop()
        pos = self.slider.value()

        self.mediaPlayer.set_position(pos / 100000)
        self.timer.start()
        # self.slider.setValue(pos)



    def get_position(self):
        p = self.mediaPlayer.position()

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):

        # self.slider.setValue(position)
        self.timer.stop()
        pos = self.slider.value()

        self.mediaPlayer.set_position(position / 100000  )# / (self.media.get_duration()))
        self.timer.start()


    def handle_errors(self):
        # TODO : create error handlers
        self.playBtn.setEnabled(False)
        self.label.setText("Error: " + self.mediaPlayer.errorString())

    def getSliderValue(self):

        value = int(self.mediaPlayer.get_position() * (self.media.get_duration()))
        value = value // 1000
        min, sec = divmod(value, 60)
        hour, min = divmod(min, 60)

        return "%d:%02d:%02d" % (hour, min, sec)

    def getDurationValue(self):

        value = int(self.media.get_duration())
        value = value // 1000
        min, sec = divmod(value, 60)
        hour, min = divmod(min, 60)

        return "%d:%02d:%02d" % (hour, min, sec)

    def onstartbuttonClicked(self, panel_index, i):
        value = self.getSliderValue()

        self.startingTimelist[panel_index][i].setText(str(value))
        self.startingTimelist[panel_index][i].setStyleSheet('color: white')
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        self.clearEntryBtn[panel_index][i].setEnabled(True)

    def onendbuttonClicked(self, panel_index, i):
        value = self.getSliderValue()

        self.endingTimelist[panel_index][i].setText(str(value))
        self.endingTimelist[panel_index][i].setStyleSheet('color: white')
        self.saveEntryBtn[panel_index][i].setEnabled(True)
        self.clearEntryBtn[panel_index][i].setEnabled(True)

    def onsaveEntryBtnClicked(self, panel_index, i):
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        form_title = self.form_title[panel_index].text()
        task_name = self.tasklist[panel_index][i].text()
        starting_time = self.startingTimelist[panel_index][i].text()
        ending_time = self.endingTimelist[panel_index][i].text()
        with open('{}/{}.txt'.format(self.save_directory, form_title), 'a') as f:
            f.write('{} : ({},{})\n'.format(task_name, starting_time, ending_time))

        #self.startingTimelist[panel_index][i].setText('0')
        #self.endingTimelist[panel_index][i].setText('0')

    def onclearEntryBtnClicked(self, panel_index, i):
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        self.clearEntryBtn[panel_index][i].setEnabled(False)
        self.startingTimelist[panel_index][i].setText('0')
        self.endingTimelist[panel_index][i].setText('0')

    def screenshotCall(self):
        frame_num = int(self.mediaPlayer.get_position() * (self.media.get_duration()))
        self.cap.set(cv2.CAP_PROP_POS_MSEC, frame_num)  # Go to the 1 msec. position
        ret, frame = self.cap.read()  # Retrieves the frame at the specified second
        cv2.imwrite \
            (self.image_save_directory + '/{}Frame{}.png'.format(str(self.vidname).split('.')[-2] ,str(frame_num)), frame)

    def buffer_frame(self, image):
        self.ImagesBuffer = image

    def update_ui(self):


        media_pos = int(self.mediaPlayer.get_position() * 100000)
        self.slider.setValue(media_pos)
        # No need to call this function if nothing is played
        if not self.mediaPlayer.is_playing():
            self.timer.stop()
            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.stop()
    def stop(self):
        """Stop player
        """
        self.mediaPlayer.stop()
        self.playBtn.setIcon(
            self.style().standardIcon(QStyle.SP_MediaPlay)
        )

    def save(self):
        value = 0

        if self.num_panels != 0:
            for panel_index in range(1, self.num_panels + 1):
                for i in range(len(self.startingTimelist[panel_index])):
                    if self.startingTimelist[panel_index][i].text() != str(value) and self.endingTimelist[panel_index][i].text() != str(value):
                        self.onsaveEntryBtnClicked(panel_index, i)


    def clearPanels(self):
        value = 0

        if self.num_panels != 0:

            for panel_index in range(1,self.num_panels+1):

                for i in range(len(self.startingTimelist[panel_index])):

                    self.startingTimelist[panel_index][i].setText(str(value))
                    self.startingTimelist[panel_index][i].setStyleSheet('color: white')
                    self.endingTimelist[panel_index][i].setText(str(value))
                    self.endingTimelist[panel_index][i].setStyleSheet('color: white')
                    self.saveEntryBtn[panel_index][i].setEnabled(False)
                    self.clearEntryBtn[panel_index][i].setEnabled(False)

    def close(self):
        sys.exit(app.exec_())


app = QApplication(sys.argv)
window = Window()
sys.exit(app.exec_())
