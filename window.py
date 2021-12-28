import binascii
import datetime
import json
import queue
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QWidget, QListWidgetItem
from PyQt5.QtCore import QTimer, Qt, QSize
from core.logger import logger
from core.package_cotain import Dealer
from db.table import DbConfig, SysConfig
from ui.MainWindow import Ui_MainWindow
from ui.command_items import Items
from ui.tool_set import Ui_Dialog
from ui.command_list import Ui_Dialog as Command_Ui_Dialog
import ui.source_rc
from core.serial_handler import ComHandler
from core.key import Key


class SetDialog(Ui_Dialog, QWidget):
    def __init__(self,  *args, **kwargs):
        super(SetDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.__init_ui()

    def __init_ui(self):
        self.setWindowTitle('设置')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.radioButton_3.setChecked(True)
        self.radioButton_4.setChecked(True)
        self.radioButton_6.setEnabled(False)


class CommandList(Command_Ui_Dialog, QWidget):
    def __init__(self, send_fun, *args, **kwargs):
        super(CommandList, self).__init__(*args, **kwargs)
        self.send_fun = send_fun
        self.item_index = {}
        self.setupUi(self)
        self.setWindowTitle('快捷指令')
        self.move(1750, 340)
        self.__connect()
        self.config = DbConfig()
        # self.load_config()
        self.fill_combobox()

    def __connect(self):
        self.pushButton.clicked.connect(self.add_list_item)
        self.comboBox.currentIndexChanged.connect(self.show_category_result)
        self.pushButton_4.clicked.connect(self.search_result)

    def add_list_item(self):
        current_id = self.config.insert_config()
        self.add_item(current_id)

    def load_config(self):
        for i in self.config.select_all():
            cid, category, name, command, is_hex = i
            self.add_item(cid, category, name, command, is_hex)

    def add_item(self, cid, category=None, name=None, command=None, is_hex=0):
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 50))
        self.item_index[cid] = item
        widget = Items(cid=cid, category=category, name=name, command=command, is_hex=is_hex,
                       save_fun=self.config.update_config, refresh_combobox=self.fill_combobox,
                       delete_fun=self.delete_item, send_fun=self.send_fun)
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)

    def delete_item(self, cid):
        self.listWidget.takeItem([i for i in self.item_index.keys()].index(cid))
        self.item_index.pop(cid)
        self.config.delete(cid)
        self.repaint()
        self.fill_combobox()

    def fill_combobox(self):
        all_category = self.config.get_category()
        if all_category:
            self.comboBox.clear()
            self.comboBox.addItem("ALL")
            [self.comboBox.addItem(i[0]) for i in all_category]

    def show_category_result(self):
        current_text = self.comboBox.currentText()
        self.listWidget.clear()
        if current_text == "ALL":
            self.load_config()
        else:
            res = self.config.select_all("where CATEGORY = '{}'".format(current_text))
            for i in res:
                cid, category, name, command, is_hex = i
                self.add_item(cid, category, name, command, is_hex)

    def search_result(self):
        search = self.lineEdit.text()
        self.listWidget.clear()
        sql = "where "
        sql += "CATEGORY like '%{value}%' OR NAME like '%{value}%' OR COMMAND like '%{value}%'".format(value=search)
        res = self.config.select_all(sql)
        for i in res:
            cid, category, name, command, is_hex = i
            self.add_item(cid, category, name, command, is_hex)


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.set_dialog = SetDialog()
        self.command_list = CommandList(self.com_send)
        self.sys_config = SysConfig()
        self.setupUi(self)  # 初始化ui
        self.setWindowTitle('串口调试工具')
        self.com_response_queue = queue.Queue()
        self.com_dealer = ComHandler(self.com_response_queue)
        self.__connect()
        self.com_deal_timer = QTimer()
        self.com_deal_timer.timeout.connect(self.deal_com_response)
        self.com_deal_timer.start(5)
        self.com_dealer.search()

        self.receive_queue = queue.Queue()
        self.package_dealer = Dealer(self.receive_queue)
        self.package_dealer.msg.connect(self.com_receive)

        self.receive_format = "utf-8"
        self.send_format = "utf-8"

        self.load_sys_config()

    def __connect(self):
        self.pushButton_5.clicked.connect(self.com_dealer.search)
        self.pushButton_2.clicked.connect(self.open_current_com)
        self.pushButton_4.clicked.connect(self.com_send)
        self.pushButton_3.clicked.connect(self.setting)
        self.pushButton_8.clicked.connect(self.command_list.show)
        # 设置框的信号绑定
        self.set_dialog.radioButton.clicked.connect(lambda: self.rec_setting_select("bytes"))
        self.set_dialog.radioButton_2.clicked.connect(lambda: self.rec_setting_select("hex"))
        self.set_dialog.radioButton_3.clicked.connect(lambda: self.rec_setting_select("utf-8"))
        self.set_dialog.radioButton_4.clicked.connect(lambda: self.send_setting_select("utf-8"))
        self.set_dialog.radioButton_5.clicked.connect(lambda: self.send_setting_select("hex"))
        # 设置串口环回
        self.set_dialog.checkBox_2.clicked.connect(self.set_com_loop)
        # 设置大小端
        self.set_dialog.checkBox.clicked.connect(self.set_endian)
        # 设置报文拼接
        self.set_dialog.checkBox_3.clicked.connect(self.set_package_contain)
        # 设置拼接字符串的头部
        self.set_dialog.lineEdit.editingFinished.connect(self.set_package_head)
        # 设置拼接字符串的长度字节所在位置
        self.set_dialog.lineEdit_2.editingFinished.connect(self.set_package_len)

    def load_sys_config(self):
        # 加载本地配置
        res = self.sys_config.get_by_key(Key.receive_type)
        if res is not None:
            self.receive_format = res
            if res == "bytes":
                self.set_dialog.radioButton.setChecked(True)
            elif res == "hex":
                self.set_dialog.radioButton_2.setChecked(True)
            else:
                self.set_dialog.radioButton_3.setChecked(True)
        res = self.sys_config.get_by_key(Key.send_type)
        if res is not None:
            self.send_format = res
            if res == "hex":
                self.set_dialog.radioButton_5.setChecked(True)
            else:
                self.set_dialog.radioButton_4.setChecked(True)
        # 设置串口环回
        res = self.sys_config.get_by_key(Key.loop_deal)
        if res is not None:
            self.set_dialog.checkBox_2.setChecked(True if res else False)
        # 设置大小端
        res = self.sys_config.get_by_key(Key.endian)
        if res is not None:
            self.package_dealer.endian = res
            self.set_dialog.checkBox.setChecked(True if res else False)
        # 设置是否开启报文拼接
        res = self.sys_config.get_by_key(Key.package_contain)
        if res is not None:
            self.set_dialog.checkBox_3.setChecked(True if res else False)
            self.package_dealer.is_start = True if res else False
            if res:
                self.set_dialog.lineEdit.setEnabled(True)
                self.set_dialog.lineEdit_2.setEnabled(True)
        # 设置报文头部
        res = self.sys_config.get_by_key(Key.package_head)
        if res is not None:
            self.package_dealer.set_head(res)
            self.set_dialog.lineEdit.setText(res)
        # 设置报文长度字节所在位置
        res = self.sys_config.get_by_key(Key.package_len)
        if res is not None:
            self.package_dealer.set_len(res)
            self.set_dialog.lineEdit_2.setText(res)

    def deal_com_response(self):
        if len(self.com_response_queue.queue):
            rec_data = self.com_response_queue.get()
            report_type, report_time, com_name, code, msg, data = tuple(rec_data.values())
            log_msg = "{}report_time:{} type:{} code:{} ".format(com_name, report_time, report_type.center(7), code)
            if report_type in ("open", "close") or code != 0:
                log_msg += "msg:{}".format(msg)
            elif report_type in ("receive", "send"):
                msg_bin = data["bin"] if isinstance(data, dict) else data
                log_msg += "len:{} data:{}".format(len(msg_bin), msg_bin)
            else:
                log_msg += "result:" + ",".join([i.device for i in data])
            logger.info(log_msg)
            if report_type == "search":
                self.fresh_com(data)
                res = self.sys_config.get_by_key(Key.COM_SETTING)
                if res is not None:
                    self.lineEdit.setText(res["baud_rate"])
                    self.comboBox.setCurrentText(res["com_name"])
            elif report_type == "open":
                if code == 0:
                    self.pushButton_2.setText("关闭")
                    self.lineEdit.setEnabled(False)
                    self.comboBox.setEnabled(False)
                    self.pushButton_5.setEnabled(False)
                    self.sys_config.update(key="COM_SETTING", save_type="json",
                                           value=json.dumps({"com_name": self.comboBox.currentText(),
                                                             "baud_rate": self.lineEdit.text()}))
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
                    self.receive_queue.put(data)
                else:
                    self.com_dealer.close()
            elif report_type == "send":
                if code == 0:
                    send_bin, fun_name, args = tuple(data.values())
                    self.textBrowser.append("[  SEND ][{}]:{}".format(
                        datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S.%f"),
                        self.turn_data(data["bin"], self.receive_format)))
                    if fun_name is not None:
                        try:
                            fun_name(*args)
                        except Exception as e:
                            return e
                else:
                    QMessageBox(self).critical(self, "ERROR", msg)
                    self.com_dealer.close()
        return None

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

    def com_send(self, send_data=None, is_hex=False):
        if not self.com_dealer.com.isOpen():
            QMessageBox().critical(self, "ERROR", "请先打开串口")
            return
        if not isinstance(send_data, str):
            data = self.textEdit.toPlainText()
        else:
            data = send_data
        if data == "":
            return
        if (self.send_format == "hex" and not isinstance(send_data, str)) or is_hex:
            data = data.replace(" ", "")
            try:
                data = binascii.a2b_hex(data)
            except Exception as e:
                QMessageBox().critical(self, "ERROR", "this not hex str:{}".format(e))
                return e
            self.com_dealer.send(data, gap=48)
        else:
            self.com_dealer.send(data.encode(errors="ignore"), gap=48)

    def com_receive(self, input_bytes):
        self.textBrowser.append("[RECEIVE][{}]:{}".format(datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S.%f"),
                                                          self.turn_data(input_bytes, self.receive_format)))

    def setting(self):
        self.set_dialog.show()

    def rec_setting_select(self, select):
        self.receive_format = select
        self.sys_config.update(key=Key.receive_type, save_type="str", value=select)

    def send_setting_select(self, select):
        self.send_format = select
        self.sys_config.update(key=Key.send_type, save_type="str", value=select)

    @staticmethod
    def turn_data(data, frm):
        if frm == "bytes":
            return data
        elif frm == "hex":
            return data.hex(" ")
        elif frm == "utf-8":
            return data.decode(errors="ignore")

    def set_com_loop(self, flag):
        self.sys_config.update(key=Key.loop_deal, save_type="int", value=1 if flag else 0)

    def set_endian(self, flag):
        self.package_dealer.endian = 1 if flag else 0
        self.sys_config.update(key=Key.endian, save_type="int", value=1 if flag else 0)

    def set_package_contain(self, flag):
        self.package_dealer.is_start = flag
        self.sys_config.update(key=Key.package_contain, save_type="int", value=1 if flag else 0)

    def set_package_head(self):
        self.package_dealer.set_head(self.set_dialog.lineEdit.text())
        self.sys_config.update(key=Key.package_head, save_type="str", value=self.set_dialog.lineEdit.text())

    def set_package_len(self):
        self.package_dealer.set_len(self.set_dialog.lineEdit_2.text())
        self.sys_config.update(key=Key.package_len, save_type="str", value=self.set_dialog.lineEdit_2.text())


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon(':/img/img/ACT011.png'))
    win = MainWindow()
    win.show()
    app.exec_()
