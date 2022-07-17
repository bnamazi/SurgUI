from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QAction,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QSizePolicy,
    QFileDialog,
    QLineEdit,
    QFormLayout,
    QGroupBox,
    QScrollArea,
    QMainWindow,
    QComboBox,
)
import sys
import os
import platform
import cv2
import vlc
from PyQt5.QtMultimedia import (
    QMediaContent,
    QMediaPlayer,
    QVideoFrame,
    QAbstractVideoSurface,
    QAbstractVideoBuffer,
    QVideoSurfaceFormat,
)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QPalette, QImage, QPainter, QFont
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QPoint, QRect, QObject
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets
from functools import partial
import subprocess
import json
import time


class Slider(QSlider):
    def mousePressEvent(self, event, window):
        if event.button() == Qt.LeftButton:
            event.accept()
            x = event.pos().x()
            value = (
                self.maximum() - self.minimum()
            ) * x / self.width() + self.minimum()
            window.timer.stop()
            # pos = self.slider.value()

            window.mediaPlayer.set_position(value / 100000)
            window.timer.start()
        else:
            return super().mousePressEvent(window, event)

    def mouseMoveEvent(self, event, window):
        event.accept()
        x = event.pos().x()
        value = (self.maximum() - self.minimum()) * x / self.width() + self.minimum()
        window.mediaPlayer.set_position(value / 100000)
        self.setValue(value)


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Surgical Video Player")
        self.setGeometry(350, 100, 700, 500)
        self.setWindowIcon(QIcon("player.png"))

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

        self.instance = vlc.Instance()
        self.media = None
        # create media player object
        self.mediaPlayer = (
            self.instance.media_player_new()
        )  # QMediaPlayer(None, QMediaPlayer.VideoSurface)

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
        openBtn = QPushButton("Open Video")
        openBtn.clicked.connect(self.open_video)

        # create button for taking a snapshot
        snapBtn = QPushButton("snapshot (save the image)")
        snapBtn.clicked.connect(self.screenshotCall)
        # snapBtn.setEnabled(True)
        self.ImagesBuffer = None

        labelmeBtn = QPushButton("Annotate (labelme)")
        labelmeBtn.clicked.connect(self.annotate)

        # create button for playing
        self.playBtn = QPushButton()
        self.playBtn.setEnabled(False)
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.play_video)

        self.playbackspeedBtn = QComboBox()  # QPushButton('2X')
        self.playbackspeedBtn.addItems(["1X", "1.5X", "2X", "3X"])
        self.playbackspeedBtn.currentIndexChanged.connect(self.set_speed)

        # create slider
        self.slider = QSlider(Qt.Horizontal)
        # self.slider.setRange(0, 0)
        # self.slider.setSingleStep(5000)
        self.slider.setMaximum(100000)
        self.slider.sliderMoved.connect(self.position_changed)
        # self.slider.valueChanged.connect(self.set_position)
        self.slider.sliderPressed.connect(self.position_changed)

        # create LCD for displaying the position of the slider
        # self.lcd = QLCDNumber(self)
        self.l = QLabel("0:00:00")
        self.l.setStyleSheet("color: white")
        self.slider.valueChanged.connect(self.display_time)  # (self.lcd.display)
        self.d = QLabel("0:00:00")
        self.d.setStyleSheet("color: white")

        # create label
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # create hbox layout
        hboxLayout = QHBoxLayout()
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        # set widgets to the hbox layout
        # hboxLayout.addWidget(openBtn)
        hboxLayout.addWidget(self.playBtn)
        hboxLayout.addWidget(self.playbackspeedBtn)
        hboxLayout.addWidget(self.l)
        hboxLayout.addWidget(self.slider)
        hboxLayout.addWidget(self.d)
        hboxLayout.addWidget(self.playBtn)

        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(snapBtn)
        bottomLayout.addWidget(labelmeBtn)

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
        self.ratingButtonslist = [None] * 10
        self.yesButtonlist = [None] * 10
        self.noButtonlist = [None] * 10
        self.ratingItemlist = [None] * 10
        self.groupButtonlist = [None] * 10

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)

        self.setLayout(self.mainLayout)

        self.parrentDirectory = None
        self.save_directory = None
        self.vidname = None
        self.image = None
        self.image_save_directory = None
        self.segmentation_labels = set()

        # create menu bar
        menuBar = QMenuBar(self)
        # menuBar.setStyleSheet("color: white")
        fileMenu = menuBar.addMenu("&File")
        HelpMenu = menuBar.addMenu("&Help")

        openVideoAction = QAction("&Open Video", self)
        openVideoAction.setShortcut("Ctrl+O")
        openVideoAction.setStatusTip("Open Video")
        openVideoAction.triggered.connect(self.open_video)

        addPanelAction = QAction("&Add Panel", self)
        addPanelAction.setStatusTip("Add Panel")
        addPanelAction.triggered.connect(self.add_panel)

        addTimePanelFileAction = QAction("&Add Timestamping Panel", self)
        addTimePanelFileAction.setStatusTip("Add Timestamping Panel From File")
        addTimePanelFileAction.triggered.connect(self.add_time_panel_from_file)

        addRatingPanelFileAction = QAction("&Add Rating Panel", self)
        addRatingPanelFileAction.setStatusTip("Add Rating Panel From File")
        addRatingPanelFileAction.triggered.connect(self.add_rating_panel_from_file)

        saveEntriesAction = QAction("&Save", self)
        saveEntriesAction.setStatusTip("Save all entries")
        saveEntriesAction.setShortcut("Ctrl+S")
        saveEntriesAction.triggered.connect(self.save)

        clearPanelsAction = QAction("&Clear Panels", self)
        clearPanelsAction.setStatusTip("Clear all panels")
        clearPanelsAction.setShortcut("Ctrl+C")
        clearPanelsAction.triggered.connect(self.clearPanels)

        changeSaveDirectoryAction = QAction("&Change Save Directory", self)
        changeSaveDirectoryAction.setStatusTip("Change Save Directory")
        changeSaveDirectoryAction.triggered.connect(self.changeDirectory)

        exitAction = QAction("&Exit", self)
        exitAction.setStatusTip("Exit")
        exitAction.setShortcut("Ctrl+Q")
        exitAction.triggered.connect(self.close)

        # fileMenu.addAction(addPanelAction)
        fileMenu.addAction(openVideoAction)
        fileMenu.addAction(addTimePanelFileAction)
        fileMenu.addAction(addRatingPanelFileAction)
        fileMenu.addAction(changeSaveDirectoryAction)
        fileMenu.addAction(saveEntriesAction)
        fileMenu.addAction(clearPanelsAction)
        fileMenu.addAction(exitAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.play_video()

        elif event.key() == Qt.Key_Right:
            p = self.slider.value()
            p = p + int(500000000 / self.media.get_duration())
            self.set_position(p)

        elif event.key() == Qt.Key_Left:

            p = self.slider.value()
            p = p - int(500000000 / self.media.get_duration())
            self.set_position(p)

        elif event.key() == Qt.Key_F5:

            self.close()
        else:

            super().keyPressEvent(event)

    def open_video(self):
        # opens video file, create the directory for the videos outputs, play the video
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            filter=(
                "Video files (*.MP4;*.AVI;*.MPG;*.MPEG;"
                "*.MOV;*.mp4;*.avi;*.mpg;*.mpeg;);; "
                "All files(*.*)"
            ),
        )

        if filename != "":
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

            if not self.parrentDirectory:
                self.parrentDirectory = "./outputs"
                if not os.path.exists(self.parrentDirectory):
                    os.mkdir(self.parrentDirectory)

            self.vidname = os.path.basename(filename)
            print("Saving directory: ", self.parrentDirectory + "/" + self.vidname)
            if not os.path.exists(self.parrentDirectory + "/" + self.vidname):
                os.mkdir(self.parrentDirectory + "/" + self.vidname)
            self.save_directory = self.parrentDirectory + "/" + self.vidname

            if not os.path.exists(
                self.parrentDirectory + "/" + self.vidname + "/images"
            ):
                os.mkdir(self.parrentDirectory + "/" + self.vidname + "/images")
            self.image_save_directory = (
                self.parrentDirectory + "/" + self.vidname + "/images"
            )

            # clear panels
            if self.num_panels > 0:
                self.clearPanels()
                for panel_index in range(1, self.num_panels + 1):
                    if self.groupButtonlist[panel_index]:
                        if not os.path.exists(
                            self.save_directory
                            + "/"
                            + self.form_title[panel_index].text()
                            + "_scores.txt"
                        ):
                            with open(
                                "{}/{}_scores.txt".format(
                                    self.save_directory,
                                    self.form_title[panel_index].text(),
                                ),
                                "a",
                            ) as out:
                                for i in range(len(self.groupButtonlist[panel_index])):
                                    out.write(
                                        "{} \n".format(
                                            self.tasklist[self.panel_index][i].text()
                                        )
                                    )
                        else:
                            with open(
                                "{}/{}_scores.txt".format(
                                    self.save_directory,
                                    self.form_title[panel_index].text(),
                                ),
                                "r",
                            ) as f:
                                lines = f.readlines()
                                for line in lines:
                                    rating_item = line.split(" : ")[0]

                                    if len(line.split(" : ")) == 2:
                                        score = line.split(" : ")[1]

                                        for i in range(
                                            len(self.groupButtonlist[panel_index])
                                        ):
                                            if (
                                                self.tasklist[panel_index][i].text()
                                                == rating_item
                                            ):
                                                for j in range(
                                                    len(
                                                        self.ratingButtonslist[
                                                            panel_index
                                                        ][i]
                                                    )
                                                ):
                                                    print(
                                                        self.ratingButtonslist[
                                                            panel_index
                                                        ][i][j].text(),
                                                        score,
                                                    )
                                                    if int(
                                                        self.ratingButtonslist[
                                                            panel_index
                                                        ][i][j].text()
                                                    ) == int(score):
                                                        self.ratingButtonslist[
                                                            panel_index
                                                        ][i][j].setChecked(True)

                                                # if score == 'Yes\n':
                                                #     self.yesButtonlist[panel_index][i].setChecked(True)
                                                # elif score == 'No\n':
                                                #     self.noButtonlist[panel_index][i].setChecked(True)
                                    # load existing annotations

    def play_video(self):
        if self.mediaPlayer.is_playing():
            self.mediaPlayer.pause()
            self.is_paused = True
            ##self.mediaPlayer_g.pause()
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.timer.stop()

        else:
            self.mediaPlayer.play()
            ##self.mediaPlayer_g.play()
            self.timer.start()
            self.is_paused = False
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def changeDirectory(self):
        self.parrentDirectory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Folder"
        )

        if self.vidname:
            if not os.path.exists(self.parrentDirectory + "/" + self.vidname):
                os.mkdir(self.parrentDirectory + "/" + self.vidname)
            self.save_directory = self.parrentDirectory + "/" + self.vidname

            if not os.path.exists(
                self.parrentDirectory + "/" + self.vidname + "/images"
            ):
                os.mkdir(self.parrentDirectory + "/" + self.vidname + "/images")
            self.image_save_directory = (
                self.parrentDirectory + "/" + self.vidname + "/images"
            )

            print("Saving directory: ", self.parrentDirectory + "/" + self.vidname)

    def display_time(self):

        time = self.getSliderValue()
        self.l.setText("{}".format(str(time)))

    def add_panel(self):
        # for manually added panels
        pass

    def onpanelRemoveBtnClicked(self, panel_index):
        pass
        # self.mainLayout.removeWidget(self.scroll[panel_index]) deleteLater()

    def add_time_panel_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Text", filter="Text files (*.txt)"
        )

        if filename != "":
            title = str(os.path.basename(filename)).split(".")[0]
            with open(filename) as f:
                lines = f.read().splitlines()
            print("Opened time panel:", title)

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
            self.form_title[self.panel_index].setStyleSheet("color: white")
            self.form_title[self.panel_index].setAlignment(Qt.AlignCenter)
            self.form_title[self.panel_index].setFont(
                QFont("Times", 12, weight=QFont.Bold)
            )
            self.panelRemoveBtn[self.panel_index] = QPushButton("Exit")
            self.panelRemoveBtn[self.panel_index].clicked.connect(
                partial(self.onpanelRemoveBtnClicked, self.panel_index)
            )

            self.formLayout[self.panel_index].addRow(
                self.form_title[self.panel_index]
            )  # , self.panelRemoveBtn[self.panel_index])

            for i, line in enumerate(lines):
                line = line.split("#")

                self.tasklist[self.panel_index].append(QLabel(line[0]))
                self.tasklist[self.panel_index][i].setStyleSheet(
                    "background-color: black ; color: white"
                )
                self.tasklist[self.panel_index][i].setFont(
                    QFont("Times", 10, weight=QFont.Bold)
                )
                self.tasklist[self.panel_index][i].setWordWrap(True)
                self.startingButtonlist[self.panel_index].append(QPushButton("starts"))
                self.startingButtonlist[self.panel_index][i].setFixedWidth(50)
                self.startingTimelist[self.panel_index].append(QLabel("0"))
                self.startingTimelist[self.panel_index][i].setStyleSheet("color: white")
                self.startingButtonlist[self.panel_index][i].clicked.connect(
                    partial(self.onstartbuttonClicked, self.panel_index, i)
                )
                self.endingButtonlist[self.panel_index].append(QPushButton("ends"))
                self.endingButtonlist[self.panel_index][i].setFixedWidth(50)
                self.endingTimelist[self.panel_index].append(QLabel("0"))
                self.endingTimelist[self.panel_index][i].setStyleSheet("color: white")
                self.endingButtonlist[self.panel_index][i].clicked.connect(
                    partial(self.onendbuttonClicked, self.panel_index, i)
                )
                if len(line) == 3:
                    self.startingButtonlist[self.panel_index][i].setToolTip(line[1])
                    self.endingButtonlist[self.panel_index][i].setToolTip(line[2])
                self.saveEntryBtn[self.panel_index].append(QPushButton("save"))
                self.clearEntryBtn[self.panel_index].append(QPushButton("clear"))
                self.saveEntryBtn[self.panel_index][i].setFixedWidth(50)
                self.clearEntryBtn[self.panel_index][i].setFixedWidth(50)
                self.saveEntryBtn[self.panel_index][i].setEnabled(False)
                self.saveEntryBtn[self.panel_index][i].clicked.connect(
                    partial(self.onsaveEntryBtnClicked, self.panel_index, i)
                )
                self.clearEntryBtn[self.panel_index][i].setEnabled(False)
                self.clearEntryBtn[self.panel_index][i].clicked.connect(
                    partial(self.onclearEntryBtnClicked, self.panel_index, i)
                )

                self.formLayout[self.panel_index].addRow(
                    self.tasklist[self.panel_index][i]
                )
                self.formLayout[self.panel_index].addRow(
                    self.startingButtonlist[self.panel_index][i],
                    self.startingTimelist[self.panel_index][i],
                )
                self.formLayout[self.panel_index].addRow(
                    self.endingButtonlist[self.panel_index][i],
                    self.endingTimelist[self.panel_index][i],
                )
                self.formLayout[self.panel_index].addRow(
                    self.saveEntryBtn[self.panel_index][i],
                    self.clearEntryBtn[self.panel_index][i],
                )

            self.groupbox[self.panel_index].setLayout(self.formLayout[self.panel_index])
            self.scroll[self.panel_index] = QScrollArea()
            self.scroll[self.panel_index].setWidget(self.groupbox[self.panel_index])
            self.scroll[self.panel_index].setWidgetResizable(True)
            self.scroll[self.panel_index].setFixedWidth(150)
            self.scroll[self.panel_index].setFocusPolicy(Qt.StrongFocus)
            self.mainLayout.addWidget(self.scroll[self.panel_index])

    def add_rating_panel_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Text", filter="Text files (*.txt)"
        )

        if filename != "" and str(filename).endswith(".txt"):
            title = str(os.path.basename(filename)).split(".")[0]

            with open(filename) as f:
                lines = f.read().splitlines()
                # with open('{}/{}_scores.txt'.format(self.save_directory, title), 'w') as out:
                #     for line in lines:
                #         out.write(line + '\n')
            print("Opened rating panel:", title)

            self.num_panels += 1

            self.panel_index = self.num_panels

            self.tasklist[self.panel_index] = []

            self.yesButtonlist[self.panel_index] = []
            self.noButtonlist[self.panel_index] = []
            self.ratingButtonslist[self.panel_index] = []
            self.groupButtonlist[self.panel_index] = []

            self.yes_label = QLabel("Yes")
            self.yes_label.setStyleSheet("color: white")
            # self.yes_label.setAlignment(Qt.AlignRight)
            self.no_label = QLabel("No")
            self.no_label.setStyleSheet("color: white")
            # self.no_label.setAlignment(Qt.AlignRight)

            self.groupbox[self.panel_index] = QGroupBox()
            self.formLayout[self.panel_index] = QFormLayout()
            # self.formLayout[self.panel_index].setContentsMargins(0,0,0,0)
            self.formLayout[self.panel_index].setVerticalSpacing(10)
            self.form_title[self.panel_index] = QLabel(title)
            self.form_title[self.panel_index].setStyleSheet("color: white")
            self.form_title[self.panel_index].setAlignment(Qt.AlignCenter)
            self.form_title[self.panel_index].setFont(
                QFont("Times", 12, weight=QFont.Bold)
            )
            self.panelRemoveBtn[self.panel_index] = QPushButton("Exit")
            self.panelRemoveBtn[self.panel_index].clicked.connect(
                partial(self.onpanelRemoveBtnClicked, self.panel_index)
            )

            # firstline_empty = QLabel().setFixedWidth(100)
            # hbLayout1 = QHBoxLayout()
            # hbLayout1.addWidget(self.yes_label)
            # hbLayout1.addWidget(self.no_label)
            # hbLayout1.setContentsMargins(0, 0, 0, 0)
            #
            # container1 = QWidget()
            # container1.setLayout(hbLayout1)

            self.formLayout[self.panel_index].addRow(
                self.form_title[self.panel_index]
            )  # , self.panelRemoveBtn[self.panel_index])
            # self.formLayout[self.panel_index].addRow(firstline_empty, container1)
            for i, line in enumerate(lines):
                line = line.split("#")

                num_scores = 2
                if len(line) > 1:
                    try:
                        num_scores = int(line[1])
                    except:
                        num_scores = 2

                self.tasklist[self.panel_index].append(QLabel(line[0]))
                self.tasklist[self.panel_index][i].setStyleSheet(
                    "background-color: black ; color: white"
                )
                self.tasklist[self.panel_index][i].setFont(
                    QFont("Times", 10, weight=QFont.Bold)
                )
                self.tasklist[self.panel_index][i].setWordWrap(True)
                self.tasklist[self.panel_index][i].setFixedWidth(100)

                self.ratingButtonslist[self.panel_index].append([])

                for j in range(num_scores):
                    self.ratingButtonslist[self.panel_index][i].append(
                        QRadioButton(str(j))
                    )
                    self.ratingButtonslist[self.panel_index][i][j].setStyleSheet(
                        "background-color: black ; color: white"
                    )

                # self.yesButtonlist[self.panel_index].append(QRadioButton())
                # self.yesButtonlist[self.panel_index][i].clicked.connect()
                # self.noButtonlist[self.panel_index].append(QRadioButton())

                self.groupButtonlist[self.panel_index].append(QButtonGroup())
                for j in range(num_scores):
                    self.groupButtonlist[self.panel_index][i].addButton(
                        self.ratingButtonslist[self.panel_index][i][j]
                    )
                # self.groupButtonlist[self.panel_index][i].addButton(self.yesButtonlist[self.panel_index][i])
                # self.groupButtonlist[self.panel_index][i].addButton(self.noButtonlist[self.panel_index][i])
                self.groupButtonlist[self.panel_index][i].buttonClicked.connect(
                    partial(self.save_rating_entry, self.panel_index, i)
                )

                hbLayout = QHBoxLayout()
                for j in range(num_scores):
                    hbLayout.addWidget(self.ratingButtonslist[self.panel_index][i][j])
                # hbLayout.addWidget(self.yesButtonlist[self.panel_index][i])
                # hbLayout.addWidget(self.noButtonlist[self.panel_index][i])
                hbLayout.setContentsMargins(0, 0, 0, 0)
                container = QWidget()
                container.setLayout(hbLayout)
                self.formLayout[self.panel_index].addRow(
                    self.tasklist[self.panel_index][i], container
                )
                # self.formLayout[self.panel_index].addRow(self.startingButtonlist[self.panel_index][i],
                #                                          self.startingTimelist[self.panel_index][i])
                # self.formLayout[self.panel_index].addRow(self.endingButtonlist[self.panel_index][i],
                #                                          self.endingTimelist[self.panel_index][i])
                # self.formLayout[self.panel_index].addRow(self.saveEntryBtn[self.panel_index][i],
                #                                          self.clearEntryBtn[self.panel_index][i])

            self.groupbox[self.panel_index].setLayout(self.formLayout[self.panel_index])
            self.scroll[self.panel_index] = QScrollArea()
            self.scroll[self.panel_index].setWidget(self.groupbox[self.panel_index])
            self.scroll[self.panel_index].setWidgetResizable(True)
            self.scroll[self.panel_index].setFixedWidth(300)
            self.scroll[self.panel_index].setFocusPolicy(Qt.StrongFocus)
            self.mainLayout.addWidget(self.scroll[self.panel_index])

            if self.save_directory:
                if os.path.exists(
                    self.save_directory
                    + "/"
                    + self.form_title[self.panel_index].text()
                    + "_scores.txt"
                ):
                    # load previous ratings
                    with open(
                        "{}/{}_scores.txt".format(
                            self.save_directory,
                            self.form_title[self.panel_index].text(),
                        ),
                        "r",
                    ) as f:
                        lines = f.readlines()
                        for line in lines:
                            rating_item = line.split(" : ")[0]

                            if len(line.split(" : ")) == 2:
                                score = line.split(" : ")[1]

                                for i in range(
                                    len(self.groupButtonlist[self.panel_index])
                                ):
                                    if (
                                        self.tasklist[self.panel_index][i].text()
                                        == rating_item
                                    ):
                                        for j in range(
                                            len(
                                                self.ratingButtonslist[
                                                    self.panel_index
                                                ][i]
                                            )
                                        ):
                                            if int(
                                                self.ratingButtonslist[
                                                    self.panel_index
                                                ][i][j].text()
                                            ) == int(score):
                                                self.ratingButtonslist[
                                                    self.panel_index
                                                ][i][j].setChecked(True)
                else:
                    if self.save_directory:
                        with open(
                            "{}/{}_scores.txt".format(
                                self.save_directory,
                                self.form_title[self.panel_index].text(),
                            ),
                            "a",
                        ) as out:
                            for i in range(len(self.groupButtonlist[self.panel_index])):
                                out.write(
                                    "{} \n".format(
                                        self.tasklist[self.panel_index][i].text()
                                    )
                                )

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

        self.mediaPlayer.set_position(
            position / 100000
        )  # / (self.media.get_duration()))
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
        self.startingTimelist[panel_index][i].setStyleSheet("color: white")
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        self.clearEntryBtn[panel_index][i].setEnabled(True)

    def onendbuttonClicked(self, panel_index, i):
        value = self.getSliderValue()

        self.endingTimelist[panel_index][i].setText(str(value))
        self.endingTimelist[panel_index][i].setStyleSheet("color: white")
        self.saveEntryBtn[panel_index][i].setEnabled(True)
        self.clearEntryBtn[panel_index][i].setEnabled(True)

    def onsaveEntryBtnClicked(self, panel_index, i):
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        form_title = self.form_title[panel_index].text()
        task_name = self.tasklist[panel_index][i].text()
        starting_time = self.startingTimelist[panel_index][i].text()
        ending_time = self.endingTimelist[panel_index][i].text()
        with open("{}/{}.txt".format(self.save_directory, form_title), "a") as f:
            f.write("{} : ({},{})\n".format(task_name, starting_time, ending_time))

        # self.startingTimelist[panel_index][i].setText('0')
        # self.endingTimelist[panel_index][i].setText('0')

    def onclearEntryBtnClicked(self, panel_index, i):
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        self.clearEntryBtn[panel_index][i].setEnabled(False)
        self.startingTimelist[panel_index][i].setText("0")
        self.endingTimelist[panel_index][i].setText("0")

    def screenshotCall(self):
        # pause video if playing
        if self.mediaPlayer.is_playing():
            # self.set_speed(0)
            self.mediaPlayer.pause()
            self.is_paused = True
            ##self.mediaPlayer_g.pause()
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.timer.stop()

        if self.vidname:
            frame_num = int(
                self.mediaPlayer.get_position() * (self.media.get_duration())
            )
            self.cap.set(cv2.CAP_PROP_POS_MSEC, frame_num)  # Go to the 1 msec. position
            (
                ret,
                self.frame,
            ) = self.cap.read()  # Retrieves the frame at the specified second
            if self.image_save_directory:
                self.image = self.image_save_directory + "/{}Frame{}.png".format(
                    str(self.vidname).split(".")[-2], str(frame_num)
                )
            cv2.imwrite(self.image, self.frame)

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
        """Stop player"""
        self.mediaPlayer.stop()
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def set_speed(self, i):
        if i == 0:
            self.mediaPlayer.set_rate(1)
        elif i == 1:
            self.mediaPlayer.set_rate(1.5)
        elif i == 2:
            self.mediaPlayer.set_rate(2)
        elif i == 3:
            self.mediaPlayer.set_rate(3)

    def save(self):
        value = 0

        if self.num_panels != 0:
            for panel_index in range(1, self.num_panels + 1):
                if self.startingButtonlist[panel_index]:
                    for i in range(len(self.startingButtonlist[panel_index])):
                        if self.saveEntryBtn[panel_index][i].isEnabled():
                            # if self.startingTimelist[panel_index][i].text() != str(value) and self.endingTimelist[panel_index][
                            #   i].text() != str(value):
                            self.onsaveEntryBtnClicked(panel_index, i)

    def annotate(self):
        if self.image_save_directory:
            for json_file in os.listdir(self.image_save_directory):
                if json_file.endswith(".json"):
                    with open(
                        os.path.join(self.image_save_directory, json_file)
                    ) as annotation_file:
                        data = json.load(annotation_file)
                        for shape in data["shapes"]:
                            if shape["label"]:
                                if not shape["label"] in self.segmentation_labels:
                                    self.segmentation_labels.add(shape["label"])

        if self.image:
            if len(self.segmentation_labels) == 0:
                subprocess.Popen(
                    [
                        "labelme",
                        "{}".format(self.image),
                        "--output",
                        "{}".format(
                            self.image.replace(self.image.split(".")[-1], "json")
                        ),
                    ]
                )
            else:
                labels = ",".join(l for l in self.segmentation_labels)
                print(labels)
                subprocess.Popen(
                    [
                        "labelme",
                        "{}".format(self.image),
                        "--output",
                        "{}".format(
                            self.image.replace(self.image.split(".")[-1], "json")
                        ),
                        "--labels",
                        labels,
                    ]
                )

    def save_rating_entry(self, panel_index, i):
        if self.vidname:
            form_title = self.form_title[panel_index].text()
            rating_item = self.tasklist[panel_index][i].text()
            score = None

            for j in range(len(self.ratingButtonslist[panel_index][i])):
                if self.ratingButtonslist[panel_index][i][j].isChecked():
                    score = self.ratingButtonslist[panel_index][i][j].text()

            # if self.yesButtonlist[panel_index][i].isChecked():
            #     score = 'Yes'
            # elif self.noButtonlist[panel_index][i].isChecked():
            #     score = 'No'

            with open(
                "{}/{}_scores.txt".format(self.save_directory, form_title), "r"
            ) as f:
                lines = f.readlines()
                for index, line in enumerate(lines):
                    if line.startswith(rating_item):
                        lines[index] = "{} : {}\n".format(rating_item, score)

            with open(
                "{}/{}_scores.txt".format(self.save_directory, form_title), "w"
            ) as f:
                for line in lines:
                    f.write(line)

    def clearPanels(self):
        value = 0

        if self.num_panels != 0:

            for panel_index in range(1, self.num_panels + 1):

                if self.startingTimelist[panel_index]:
                    for i in range(len(self.startingTimelist[panel_index])):
                        self.startingTimelist[panel_index][i].setText(str(value))
                        self.startingTimelist[panel_index][i].setStyleSheet(
                            "color: white"
                        )
                        self.endingTimelist[panel_index][i].setText(str(value))
                        self.endingTimelist[panel_index][i].setStyleSheet(
                            "color: white"
                        )
                        self.saveEntryBtn[panel_index][i].setEnabled(False)
                        self.clearEntryBtn[panel_index][i].setEnabled(False)
                elif self.groupButtonlist[panel_index]:
                    for i in range(len(self.groupButtonlist[panel_index])):
                        self.groupButtonlist[panel_index][i].setExclusive(False)
                        for j in range(len(self.ratingButtonslist[panel_index][i])):
                            if self.ratingButtonslist[panel_index][i][j]:
                                self.ratingButtonslist[panel_index][i][j].setChecked(
                                    False
                                )
                        # self.yesButtonlist[panel_index][i].setChecked(False)
                        # self.noButtonlist[panel_index][i].setChecked(False)
                        self.groupButtonlist[panel_index][i].setExclusive(True)
                        # unchdeck all

    def close(self):
        sys.exit(app.exec_())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec_())
