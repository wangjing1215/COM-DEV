from PyQt5 import QtCore, QtGui, QtWidgets


class Items(QtWidgets.QWidget):
    def __init__(self, cid=0, category=None, name=None, command=None, is_hex=0, send_fun=None, delete_fun=None,
                 save_fun=None, refresh_combobox=None):
        super(Items, self).__init__()
        # 指令的唯一id
        self.cid = cid
        # 保存函数
        self.save_fun = save_fun
        # 选择框刷新
        self.refresh_combobox = refresh_combobox
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self)
        self.label_2 = QtWidgets.QLabel(self)
        self.label_2.setText(str(cid))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.label_1 = QtWidgets.QLabel(self)
        self.label_1.setText("分类")
        self.horizontalLayout_2.addWidget(self.label_1)
        self.lineEdit_1 = QtWidgets.QLineEdit(self)
        self.horizontalLayout_2.addWidget(self.lineEdit_1)
        if category is not None:
            self.lineEdit_1.setText(category)
        self.label_3 = QtWidgets.QLabel(self)
        self.label_3.setText('名称')
        self.horizontalLayout_2.addWidget(self.label_3)
        self.lineEdit_3 = QtWidgets.QLineEdit(self)
        self.horizontalLayout_2.addWidget(self.lineEdit_3)
        if name is not None:
            self.lineEdit_3.setText(name)
        self.label_4 = QtWidgets.QLabel(self)
        self.label_4.setText('内容')
        self.horizontalLayout_2.addWidget(self.label_4)
        self.lineEdit_4 = QtWidgets.QLineEdit(self)
        self.horizontalLayout_2.addWidget(self.lineEdit_4)
        if command is not None:
            self.lineEdit_4.setText(command)
        self.is_hex = QtWidgets.QCheckBox(self)
        self.is_hex.setChecked(True if is_hex else False)
        self.label_5 = QtWidgets.QLabel(self)
        self.label_5.setText('16进制')
        self.horizontalLayout_2.addWidget(self.label_5)
        self.horizontalLayout_2.addWidget(self.is_hex)
        self.pushButton_3 = QtWidgets.QPushButton(self)
        self.pushButton_3.setText("发送")
        self.horizontalLayout_2.addWidget(self.pushButton_3)
        if send_fun is not None:
            self.pushButton_3.clicked.connect(lambda: send_fun(self.lineEdit_4.text(), self.is_hex.isChecked()))
        self.pushButton_4 = QtWidgets.QPushButton(self)
        self.pushButton_4.setText("删除")
        if delete_fun is not None:
            self.pushButton_4.clicked.connect(lambda: delete_fun(int(self.label_2.text())))
        self.horizontalLayout_2.addWidget(self.pushButton_4)

        # 加载connect
        self.__connect()

    def __connect(self):
        self.lineEdit_1.textEdited.connect(self.save_config)
        self.lineEdit_3.textEdited.connect(self.save_config)
        self.lineEdit_4.textEdited.connect(self.save_config)
        self.is_hex.clicked.connect(self.save_config)

    def save_config(self):
        if self.save_fun is None:
            return
        if self.sender() == self.lineEdit_3:
            self.save_fun(self.cid, name=self.lineEdit_3.text())
            self.refresh_combobox()
        elif self.sender() == self.lineEdit_1:
            self.save_fun(self.cid, category=self.lineEdit_1.text())
        elif self.sender() == self.lineEdit_4:
            self.save_fun(self.cid, command=self.lineEdit_4.text())
        else:
            self.save_fun(self.cid, is_hex=1 if self.is_hex.isChecked() else 0)
