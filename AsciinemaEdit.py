#!/usr/bin/env python
try:  #  support either PyQt5 or 6
    from PyQt5 import uic
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import QApplication, QMainWindow

    PyQtVersion = 5
except ImportError:
    print("trying Qt6")
    from PyQt6 import uic
    from PyQt6.QtCore import QEvent, Qt, QTimer
    from PyQt6.QtWidgets import QApplication, QMainWindow, QStyle, QFileDialog
    from PyQt6.QtGui import QPalette, QColor, QFont, QTextCursor, QFontDatabase

    PyQtVersion = 6

import struct


def rawbytes(s):
    """Convert a string to raw bytes without encoding"""
    outlist = []
    for cp in s:
        num = ord(cp)
        if num < 255:
            outlist.append(struct.pack("B", num))
        elif num < 65535:
            outlist.append(struct.pack(">H", num))
        else:
            b = (num & 0xFF0000) >> 16
            H = num & 0xFFFF
            outlist.append(struct.pack(">bH", b, H))
    return b"".join(outlist)


import sys, json
from ansi2html import Ansi2HTMLConverter

remove_codes = [
    "\u001b[?1h",  # cursor keys mode
    "\u001b[?1l",  # cursor keys mode
    "\u001b>",  # keypad mode
    "\u001b[?2004h",  # bracketed paste mode
    "\u001b[?25l",  # hide cursor
    "\u001b[?12l",  # blinking cursor
    "\u001b[?25h",  # show cursor
    "\u001b[?47l",  # alternate screen
    "\u001b[?47h",  # alternate screen
    "\u001b[?1049h",  # alternate screen
    "\u001b[?1049l",  # alternate screen
    "\u001b[?2004l",  # bracketed paste mode
    "\u001b[0m",  # reset
    "\b",  # backspace
    "\u001b8",  # restore cursor,
    "\u001b7",  # save cursor,
    "\u001b[2K",  # clear line
    "\u001b[1G",  # move to first column
    "\u001b[2J",  # clear screen
    "\u001b[0m:",  # Reset all attributes
    "\u001b[27m:",  # Disable underline
    "\u001b[24m:",  # Disable strikethrough
    "\u001b[J:",  # Clear screen from cursor down
    "\u001b[49m:",  # Set background color to default
    "\u001b[39m:",  # Set foreground color to default
    "\u001b[A:",  # Move cursor up one line
    "\u001b[0m:",  # Reset all attributes
    "\u001b[K:",  # Clear line from cursor right
    "\u001b[?1h",
    "\u001b=",
]


class MainWindow(QMainWindow):
    def __init__(self, file: str = ""):
        super(MainWindow, self).__init__()
        uic.loadUi("form.ui", self)
        self.output.setStyleSheet(
            "background-color: rgb(30,30,30);color : rgb(250,250,250);"
        )
        self.output.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.timer = QTimer()
        self.cast_data = []
        self.start_frame.setValue(0)
        self.output.ensureCursorVisible()
        self.output.setReadOnly(True)
        self.conv = Ansi2HTMLConverter(font_size="20px", line_wrap=False)
        if file != "":
            self._process_cast_file(file)
        self.current_line = 0
        self.load.clicked.connect(self.load_clicked)
        # self.startTimer(100)
        self.frame.setMinimum(0)
        self.frame.setMaximum(len(self.cast_data) - 1)
        self.frame.valueChanged.connect(self.frame_changed)
        self.frame_changed(0)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self.play_pause.setIcon(icon)
        self.play_pause.clicked.connect(self.play_pause_clicked)
        self.save_as.clicked.connect(self.save_as_clicked)

    def load_clicked(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Range",
            "",
            ("Cast File (*.cast)"),
        )
        if file_name is not None:
            self.cast_data = []
            self._process_cast_file(file_name)
            self.start_frame.setValue(0)
            self.end_frame.setValue(len(self.cast_data) - 1)
            self.frame.setMinimum(0)
            self.frame.setMaximum(len(self.cast_data) - 1)
            self.play_pause.setChecked(True)  # auto play on load

    def save_as_clicked(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Range",
            "untitled.cast",
            ("Cast File (*.cast)"),
        )
        if file_name is not None:
            with open(file_name, "w") as f:
                f.write(json.dumps(self.header) + "\n")
                for line in self.cast_data[
                    self.start_frame.value() : self.end_frame.value()
                ]:
                    frame_time = line[0]
                    if self.retime.isChecked():
                        frame_time -= self.cast_data[self.start_frame.value()][0]

                    output = f'[{frame_time}, "{line[1]}", "'
                    f.write(output)
                    escape_map = {
                        "\u001b": "\\u001b",
                        "\u0007": "\\u0007",
                        "\r": "\\r",
                        "\n": "\\n",
                        '"': '\\"',
                        "\\": "\\\\",
                        "\t": "\\t",
                        "\b": "\\b",
                    }
                    for c in line[2]:
                        f.write(escape_map.get(c, c))

                    f.write('"]\n')

    def play_pause_clicked(self, mode: bool):
        if mode:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            self.play_pause.setIcon(icon)
            self.timer.setSingleShot(False)
            self.timer.timeout.connect(self.animate)
            self.timer.setInterval(1)
            self.timer.start()
        else:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            self.play_pause.setIcon(icon)
            self.timer.stop()

    def _process_cast_file(self, file: str):
        with open(file, "rt", encoding="utf-8") as f:
            lines = f.readlines()
            self.header = json.loads(lines[0])

        for line in lines[1:]:
            to_add = eval(line)
            self.cast_data.append(to_add)
        self.last_time = self.cast_data[0][0]
        self.end_frame.setValue(len(self.cast_data) - 1)

    def _remove_backspace(self, s):
        result = ""
        i = 0
        while i < len(s):
            if s[i] == "\b":
                if i > 0:
                    result = result[:-1]  # remove previous character
                i += 1  # skip backspace character
            else:
                result += s[i]
                i += 1
        return result

    def _prepare_line(self, value):
        line_to_print = ""
        for line in self.cast_data[:value]:
            line = line[2]
            if "\u001b[H\u001b[2J" in line:
                line_to_print = ""
                continue
            if "\u001b]2;" in line:  # mac / zsh title
                line = line.replace("\u001b]2;", "")
                line = line.replace("\u001b]1;", "")  # set title
                line = line.replace("\u0007", "")
                self.setWindowTitle(line)
                continue
            if "\u001b]0;" in line:  # set title linux
                previous = ""
                if line.find("\u001b]0;") > 0:  # text before header set
                    previous = line[: line.find("\u001b]0;")]
                line = line.replace("\u001b]0;", "")
                end = line.find("\u0007")

                title = line[:end]
                self.setWindowTitle(title)
                line = previous + line[end:]
                line.rstrip()

            # junk codes
            for code in remove_codes:
                line = line.replace(code, "")
            line_to_print += line
        # print("*" * 80)
        # print(line_to_print)
        line_to_print = self._remove_backspace(line_to_print)
        # print("-" * 80)
        # print(line_to_print)
        return line_to_print

    def _print_line(self, value):
        line_to_print = self._prepare_line(value)
        if len(line_to_print) == 0:
            return
        line_html = self.conv.convert(line_to_print)

        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.textCursor().insertHtml(line_html)
        self.frame_no.setText(f"Frame {value} {self.cast_data[value][0]}")

    def _quantize(self, lst, decimals=2):
        return [round(x, decimals) for x in lst]

    def frame_changed(self, value):
        self.current_line = value
        self.output.clear()
        self._print_line(value)

    def animate(self):
        self.output.clear()
        self.frame.blockSignals(True)
        self.frame.setValue(self.current_line)
        self.frame.blockSignals(False)

        if self.current_line < self.end_frame.value():
            self._print_line(self.current_line)
            new_sleep = self.cast_data[self.current_line][0] - self.last_time
            self.last_time = self.cast_data[self.current_line][0]
            self.timer.setInterval(abs(int(new_sleep * 1000)))
            self.current_line += 1
        else:
            self.current_line = self.start_frame.value()


if __name__ == "__main__":
    app = QApplication([])
    if len(sys.argv) > 1:
        widget = MainWindow(sys.argv[1])
    else:
        widget = MainWindow()
    widget.show()
    sys.exit(app.exec())


# conv = Ansi2HTMLConverter()
# ansi = "".join(sys.stdin.readlines())
# html = conv.convert(ansi)
