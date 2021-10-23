import binascii
import queue
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QFileDialog, QWidget, QStyleOption, QStyle
from PyQt5.QtCore import QTimer, Qt

from ui.MainWindow import Ui_MainWindow
from ui.tool_set import Ui_Dialog
import ui.source_rc
from core.serial_handler import ComHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s-%(levelname)s-%(message)s')
logger = logging.getLogger("COM")


class SetDialog(Ui_Dialog, QWidget):
    def __init__(self,  *args, **kwargs):
        super(SetDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('设置')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.radioButton_3.setChecked(True)
        self.radioButton_4.setChecked(True)


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.set_dialog = SetDialog()
        self.setupUi(self)  # 初始化ui
        self.setWindowTitle('串口调试工具')
        self.com_response_queue = queue.Queue()
        self.com_dealer = ComHandler(self.com_response_queue)
        self.__connect()
        self.com_deal_timer = QTimer()
        self.com_deal_timer.timeout.connect(self.deal_com_response)
        self.com_deal_timer.start(5)
        self.com_dealer.search()

        self.receive_format = "utf-8"
        self.send_format = "utf-8"

    def __connect(self):
        self.pushButton_5.clicked.connect(self.com_dealer.search)
        self.pushButton_2.clicked.connect(self.open_current_com)
        self.pushButton_4.clicked.connect(self.com_send)
        self.pushButton_3.clicked.connect(self.setting)
        self.set_dialog.radioButton.clicked.connect(lambda: self.rec_setting_select("bytes"))
        self.set_dialog.radioButton_2.clicked.connect(lambda: self.rec_setting_select("hex"))
        self.set_dialog.radioButton_3.clicked.connect(lambda: self.rec_setting_select("utf-8"))
        self.set_dialog.radioButton_4.clicked.connect(lambda: self.send_setting_select("utf-8"))
        self.set_dialog.radioButton_5.clicked.connect(lambda: self.send_setting_select("hex"))

    def deal_com_response(self):
        if len(self.com_response_queue.queue):
            rec_data = self.com_response_queue.get()
            report_type, report_time, code, msg, data = tuple(rec_data.values())
            logger.info("[{}] type：{} code:{} msg:{} data:{}".format(report_time, report_type, code, msg, data))
            if report_type == "search":
                self.fresh_com(data)
            elif report_type == "open":
                if code == 0:
                    self.pushButton_2.setText("关闭")
                    self.lineEdit.setEnabled(False)
                    self.comboBox.setEnabled(False)
                    self.pushButton_5.setEnabled(False)
                else:
                    QMessageBox(self).critical(self, "ERROR", msg)
            elif report_type == "close":
                if code == 0:
                    self.pushButton_2.setText("开启")
                    self.lineEdit.setEnabled(True)
                    self.comboBox.setEnabled(True)
                    self.pushButton_5.setEnabled(True)
                else:
                    QMessageBox(self).critical(self, "ERROR", msg)
            elif report_type == "receive":
                if code == 0:
                    self.textBrowser.append("[RECEIVE][{}]:{}".format(report_time,
                                                                      self.turn_data(data, self.receive_format)))
                else:
                    self.com_dealer.close()
            elif report_type == "send":
                if code == 0:
                    send_bin, fun_name, args = tuple(data.values())
                    self.textBrowser.append("[SEND][{}]:{}".format(report_time,
                                                                   self.turn_data(data["bin"], self.receive_format)))
                    if fun_name is not None:
                        try:
                            fun_name(*args)
                        except Exception as e:
                            return e
                else:
                    QMessageBox(self).critical(self, "ERROR", msg)
                    self.com_dealer.close()

    def fresh_com(self, all_com):
        self.comboBox.clear()
        all_com = sorted(all_com, key=lambda k: k.device)
        for i in all_com:
            self.comboBox.addItem(i.device)

    def open_current_com(self):
        current_port = self.comboBox.currentText()
        if self.pushButton_2.text() != "关闭":
            try:
                baud_rate = int(self.lineEdit.text().strip())
            except Exception as e:
                return e
            if current_port == "":
                return
            self.com_dealer.open(current_port, baud_rate)
        else:
            self.com_dealer.close()

    def com_send(self):
        data = self.textEdit.toPlainText()
        if self.send_format == "hex":
            data = data.replace(" ", "")
            try:
                data = binascii.a2b_hex(data)
            except Exception as e:
                QMessageBox().critical(self, "ERROR", "this not hex str:{}".format(e))
                return e
            self.com_dealer.send(data, gap=48)
        else:
            self.com_dealer.send(data.encode(errors="ignore"), gap=48)

    def setting(self):
        self.set_dialog.show()

    def rec_setting_select(self, select):
        self.receive_format = select

    def send_setting_select(self, select):
        self.send_format = select

    @staticmethod
    def turn_data(data, frm):
        if frm == "bytes":
            return data
        elif frm == "hex":
            return data.hex(" ")
        elif frm == "utf-8":
            return data.decode(errors="ignore")


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon(':/img/img/ACT011.png'))
    win = MainWindow()
    win.show()
    app.exec_()
