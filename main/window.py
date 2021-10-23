import queue
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QFileDialog
from PyQt5.QtCore import QTimer, Qt
from ui.MainWindow import Ui_MainWindow
from ui import source
from core.serial_handler import ComHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s-%(levelname)s-%(message)s')
logger = logging.getLogger("COM")


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)  # 初始化ui
        self.com_response_queue = queue.Queue()
        self.com_dealer = ComHandler(self.com_response_queue)
        self.__connect()
        self.com_deal_timer = QTimer()
        self.com_deal_timer.timeout.connect(self.deal_com_response)
        self.com_deal_timer.start(5)
        self.com_dealer.search()

    def __connect(self):
        self.pushButton_5.clicked.connect(self.com_dealer.search)
        self.pushButton_2.clicked.connect(self.open_current_com)
        self.pushButton_4.clicked.connect(self.com_send)

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
                    self.textBrowser.append("[RECEIVE][{}]:{}".format(report_time, data))
                else:
                    self.com_dealer.close()
            elif report_type == "send":
                if code == 0:
                    send_bin, fun_name, args = tuple(data.values())
                    self.textBrowser.append("[SEND][{}]:{}".format(report_time, send_bin))
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
        self.com_dealer.send(data.encode(errors="ignore"), gap=48)


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon(':/img/img/ACT011.png'))
    win = MainWindow()
    win.show()
    app.exec_()
