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
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtGui import QPalette, QColor, QFont, QTextCursor, QFontDatabase

    PyQtVersion = 6

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
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi("form.ui", self)
        self.output.setStyleSheet(
            "background-color: rgb(30,30,30);color : rgb(250,250,250);"
        )
        self.output.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.cast_data = []
        self.is_visible = True
        self.conv = Ansi2HTMLConverter(font_size="20px", line_wrap=False)
        self._process_cast_file("new.cast")
        self.current_line = 0
        # self.startTimer(100)
        self.frame.setMinimum(0)
        self.frame.setMaximum(len(self.cast_data))
        self.frame.valueChanged.connect(self.frame_changed)
        self.frame_changed(0)

    def _process_cast_file(self, file: str):
        with open(file, "r") as f:
            lines = f.readlines()
            self.header = json.loads(lines[0])

        for line in lines[1:]:
            to_add = eval(line)
            self.cast_data.append(to_add)

    def remove_backspace(self, s):
        result = ""
        i = 0
        while i < len(s):
            if s[i] == "\b":
                if i > 0:
                    result = result[:-1]  # remove previous character
                    cursor = self.output.textCursor()
                    cursor.movePosition(
                        QTextCursor.MoveOperation.Left,
                        QTextCursor.MoveMode.MoveAnchor,
                        2,
                    )
                    self.output.setTextCursor(cursor)
                i += 1  # skip backspace character
            else:
                result += s[i]
                i += 1
        return result

    def frame_changed(self, value):
        self.current_line = value
        self.output.clear()
        for line in self.cast_data[:value]:
            line_to_print = line[2]
            time = line[0]
            # clear screen
            if "\u001b[H\u001b[2J" in line_to_print:
                line_to_print = line_to_print.replace("\u001b[H\u001b[2J", "")
                self.output.clear()
            if "\u001b]2;" in line_to_print:
                line_to_print = line_to_print.replace("\u001b]2;", "")
                line_to_print = line_to_print.replace("\u001b]1;", "")  # set title
                line_to_print = line_to_print.replace("\u0007", "")
                self.setWindowTitle(line_to_print)
                continue

            line_to_print = self.remove_backspace(line_to_print)
            # junk codes
            for code in remove_codes:
                line_to_print = line_to_print.replace(code, "")
            if len(line_to_print) == 0:
                continue
            line_html = self.conv.convert(line_to_print)

            self.output.moveCursor(QTextCursor.MoveOperation.End)
            self.output.textCursor().insertHtml(line_html)
            self.frame_no.setText(f"Frame {value} {time}")
            # print("*" * 80)
            # print(line)
            # print("_" * 80)
            # print(line_html)
            # self.output.insertHtml(line)

    def timerEvent(self, event):
        if self.current_line < len(self.cast_data):
            line_to_print = self.cast_data[self.current_line][2]
            if "\u001b[H\u001b[2J" in line_to_print:
                line_to_print = line_to_print.replace("\u001b[H\u001b[2J", "")
                self.output.clear()

            line_to_print = line_to_print.replace("\n", "")
            line = self.conv.convert(line_to_print)
            self.output.moveCursor(QTextCursor.MoveOperation.End)
            self.output.insertHtml(line)
            self.current_line += 1
        else:
            self.current_line = 0
            self.output.clear()


if __name__ == "__main__":
    app = QApplication([])
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())


# conv = Ansi2HTMLConverter()
# ansi = "".join(sys.stdin.readlines())
# html = conv.convert(ansi)
