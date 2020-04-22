from PyQt5.QtWidgets import QApplication, QWidget, QAction, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, \
    QSlider, QStyle, QSizePolicy, QFileDialog, QLineEdit, QFormLayout, QGroupBox, QScrollArea, QMainWindow
import sys
import os
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from functools import partial

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

        self.init_ui()

        self.showMaximized()

    def init_ui(self):
        # create the directory where the outputs for all videos are saved
        if not os.path.exists('outputs'):
            os.mkdir('outputs')

        # create media player object
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        #self.mediaPlayer.setNotifyInterval(1000)
        self.mediaPlayer.setPlaybackRate(1)

        # create videowidget object
        videowidget = QVideoWidget()
        self.mediaPlayer.setVideoOutput(videowidget)
        # media player signals
        self.mediaPlayer.stateChanged.connect(self.mediastate_changed)
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)

        # create open button
        openBtn = QPushButton('Open Video')
        openBtn.clicked.connect(self.open_video)

        # create button for taking a snapshot
        snapBtn = QPushButton('snapshot (save the image)')
        snapBtn.clicked.connect(self.get_position)
        snapBtn.setEnabled(False)

        # create button for playing
        self.playBtn = QPushButton()
        self.playBtn.setEnabled(False)
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.play_video)

        # create slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setSingleStep(5000)
        self.slider.sliderMoved.connect(self.set_position)
        self.slider.valueChanged.connect(self.set_position)

        # create LCD for displaying the position of the slider
        #self.lcd = QLCDNumber(self)
        self.l = QLabel(self)
        self.slider.valueChanged.connect(self.display_time)#(self.lcd.display)


        # create label
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # create hbox layout
        hboxLayout = QHBoxLayout()
        hboxLayout.setContentsMargins(0, 0, 0, 0)
        # set widgets to the hbox layout
        #hboxLayout.addWidget(openBtn)
        hboxLayout.addWidget(self.playBtn)
        hboxLayout.addWidget(self.l)
        hboxLayout.addWidget(self.slider)

        # create vbox layout
        vboxLayout = QVBoxLayout()
        # set widgets to the vbox layout
        #vboxLayout.addWidget(openBtn)
        vboxLayout.addWidget(videowidget)
        vboxLayout.addLayout(hboxLayout)
        vboxLayout.addWidget(snapBtn)
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

        #fileMenu.addAction(addPanelAction)
        fileMenu.addAction(addPanelFileAction)
        fileMenu.addAction(openVideoAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
                self.mediaPlayer.pause()

            else:
                self.mediaPlayer.play()

        elif event.key() == Qt.Key_Right:

            p = self.slider.value()
            p = p + 5000

            self.set_position(p)
            self.position_changed(p)

        elif event.key() == Qt.Key_Left:

            p = self.slider.value()
            p = p - 5000

            self.set_position(p)
            self.position_changed(p)

        elif event.key() == Qt.Key_F5:

            self.close()
        else:

            super().keyPressEvent(event)

    def open_video(self):
        # opens video file, create the directory for the videos outputs, play the video
        filename, _ = QFileDialog.getOpenFileName(self, "Open Video")

        if filename != '':
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
            self.playBtn.setEnabled(True)
            self.play_video()

            directory = (os.path.basename(filename))
            if not os.path.exists('outputs/'+ directory):
                os.mkdir('outputs/'+ directory)
            self.save_directory = 'outputs/'+ directory

    def play_video(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()

        else:
            self.mediaPlayer.play()

    def display_time(self):
        time = self.getSliderValue()
        self.l.setText(str(time))
        self.l.setStyleSheet('color: white')

    def mediastate_changed(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause)
            )

        else:
            self.playBtn.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay)
            )

    def add_panel(self):
        # for manually added panels
        self.num_panels += 1

        self.panel_index = self.num_panels

        self.tasklist[self.panel_index] = []
        self.startingButtonlist[self.panel_index] = []
        self.startingTimelist[self.panel_index] = []
        self.endingButtonlist[self.panel_index] = []
        self.endingTimelist[self.panel_index] = []

        self.groupbox[self.panel_index] = QGroupBox()
        self.formLayout[self.panel_index] = QFormLayout()

        self.form_title[self.panel_index] = QLineEdit()
        self.panelRemoveBtn[self.panel_index] = QPushButton('Exit')
        self.panelRemoveBtn[self.panel_index].clicked.connect(partial(self.onpanelRemoveBtnClicked, self.panel_index))

        self.formLayout[self.panel_index].addRow(self.form_title[self.panel_index])#, self.panelRemoveBtn[self.panel_index])



        for i in range(35):
            self.tasklist[self.panel_index].append(QLineEdit('Task {}'.format(str(i))))
            self.tasklist[self.panel_index][i].setStyleSheet('background-color: black ; color: white')
            self.startingButtonlist[self.panel_index].append(QPushButton('starts'))
            self.startingButtonlist[self.panel_index][i].setFixedWidth(50)
            self.startingTimelist[self.panel_index].append(QLabel('0'))
            self.startingTimelist[self.panel_index][i].setStyleSheet('color: white')
            self.startingButtonlist[self.panel_index][i].clicked.connect(partial(self.onstartbuttonClicked, self.panel_index, i))
            self.endingButtonlist[self.panel_index].append(QPushButton('ends'))
            self.endingButtonlist[self.panel_index][i].setFixedWidth(50)
            self.endingTimelist[self.panel_index].append(QLabel('0'))
            self.endingTimelist[self.panel_index][i].setStyleSheet('color: white')
            self.endingButtonlist[self.panel_index][i].clicked.connect(partial(self.onendbuttonClicked, self.panel_index, i))
            self.formLayout[self.panel_index].addRow(self.tasklist[self.panel_index][i])
            self.formLayout[self.panel_index].addRow(self.startingButtonlist[self.panel_index][i], self.startingTimelist[self.panel_index][i])
            self.formLayout[self.panel_index].addRow(self.endingButtonlist[self.panel_index][i], self.endingTimelist[self.panel_index][i])

        self.groupbox[self.panel_index].setLayout(self.formLayout[self.panel_index])
        self.scroll[self.panel_index] = QScrollArea()
        self.scroll[self.panel_index].setWidget(self.groupbox[self.panel_index])
        self.scroll[self.panel_index].setWidgetResizable(True)
        self.scroll[self.panel_index].setFixedWidth(120)
        self.mainLayout.addWidget(self.scroll[self.panel_index])

    def onpanelRemoveBtnClicked(self, panel_index):
        pass
        #self.mainLayout.removeWidget(self.scroll[panel_index])

    def add_panel_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Text")

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

        self.groupbox[self.panel_index] = QGroupBox()
        self.formLayout[self.panel_index] = QFormLayout()

        self.form_title[self.panel_index] = QLabel(title)
        self.form_title[self.panel_index].setStyleSheet('color: white')
        self.panelRemoveBtn[self.panel_index] = QPushButton('Exit')
        self.panelRemoveBtn[self.panel_index].clicked.connect(partial(self.onpanelRemoveBtnClicked, self.panel_index))

        self.formLayout[self.panel_index].addRow(self.form_title[self.panel_index])#, self.panelRemoveBtn[self.panel_index])



        for i, line in enumerate (lines):
            self.tasklist[self.panel_index].append(QLabel(line))
            self.tasklist[self.panel_index][i].setStyleSheet('background-color: black ; color: white')
            self.startingButtonlist[self.panel_index].append(QPushButton('starts'))
            self.startingButtonlist[self.panel_index][i].setFixedWidth(50)
            self.startingTimelist[self.panel_index].append(QLabel('0'))
            self.startingTimelist[self.panel_index][i].setStyleSheet('color: white')
            self.startingButtonlist[self.panel_index][i].clicked.connect(partial(self.onstartbuttonClicked, self.panel_index, i))
            self.endingButtonlist[self.panel_index].append(QPushButton('ends'))
            self.endingButtonlist[self.panel_index][i].setFixedWidth(50)
            self.endingTimelist[self.panel_index].append(QLabel('0'))
            self.endingTimelist[self.panel_index][i].setStyleSheet('color: white')
            self.endingButtonlist[self.panel_index][i].clicked.connect(partial(self.onendbuttonClicked, self.panel_index, i))
            self.saveEntryBtn[self.panel_index].append(QPushButton('save'))
            #self.saveEntryBtn[self.panel_index][i].setFixedWidth(30)
            self.saveEntryBtn[self.panel_index][i].setEnabled(False)
            self.saveEntryBtn[self.panel_index][i].clicked.connect(partial(self.onsaveEntryBtnClicked, self.panel_index, i))
            self.formLayout[self.panel_index].addRow(self.tasklist[self.panel_index][i])
            self.formLayout[self.panel_index].addRow(self.startingButtonlist[self.panel_index][i], self.startingTimelist[self.panel_index][i])
            self.formLayout[self.panel_index].addRow(self.endingButtonlist[self.panel_index][i], self.endingTimelist[self.panel_index][i] )
            self.formLayout[self.panel_index].addRow(self.saveEntryBtn[self.panel_index][i])

        self.groupbox[self.panel_index].setLayout(self.formLayout[self.panel_index])
        self.scroll[self.panel_index] = QScrollArea()
        self.scroll[self.panel_index].setWidget(self.groupbox[self.panel_index])
        self.scroll[self.panel_index].setWidgetResizable(True)
        self.scroll[self.panel_index].setFixedWidth(200)
        self.scroll[self.panel_index].setFocusPolicy(Qt.StrongFocus)
        self.mainLayout.addWidget(self.scroll[self.panel_index])

    def position_changed(self, position):
        self.slider.setValue(position)

    def get_position(self):
        p = self.mediaPlayer.position()

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.mediaPlayer.setPosition(position)

    def handle_errors(self):
        # TODO : create error handlers
        self.playBtn.setEnabled(False)
        self.label.setText("Error: " + self.mediaPlayer.errorString())

    def getSliderValue(self):

        value = self.slider.value()
        value = value // 1000
        min, sec = divmod(value, 60)
        hour, min = divmod(min, 60)

        return "%d:%02d:%02d" % (hour, min, sec)

    def onstartbuttonClicked(self, panel_index,i):
        value = self.getSliderValue()

        self.startingTimelist[panel_index][i].setText(str(value))
        self.startingTimelist[panel_index][i].setStyleSheet('color: white')
        self.saveEntryBtn[panel_index][i].setEnabled(False)

    def onendbuttonClicked(self, panel_index, i):
        value = self.getSliderValue()

        self.endingTimelist[panel_index][i].setText(str(value))
        self.endingTimelist[panel_index][i].setStyleSheet('color: white')
        self.saveEntryBtn[panel_index][i].setEnabled(True)

    def onsaveEntryBtnClicked(self, panel_index, i):
        self.saveEntryBtn[panel_index][i].setEnabled(False)
        form_title = self.form_title[panel_index].text()
        task_name = self.tasklist[panel_index][i].text()
        starting_time = self.startingTimelist[panel_index][i].text()
        ending_time = self.endingTimelist[panel_index][i].text()
        with open('{}/{}.txt'.format(self.save_directory, form_title), 'a') as f:
            f.write('{} : ({},{})\n'.format(task_name, starting_time, ending_time))



app = QApplication(sys.argv)
window = Window()
sys.exit(app.exec_())


