import sqlite3
import os
from setting import BASE_PATH


class DbBase(object):
    def __init__(self, table):
        self.db_name = os.path.join(BASE_PATH, 'com.db')
        self.conn = sqlite3.connect(self.db_name)
        self.table = table

    def check_table_exist(self):
        sql = "select name from sqlite_master where name = '{}';".format(self.table)
        return True if len(self.execute(sql)) else False

    def select_all(self):
        sql = "select * from {}".format(self.table)
        return self.execute(sql)

    def execute(self, sql, commit=False):
        try:
            self.conn = sqlite3.connect('com.db')
            c = self.conn.cursor()
            c.execute(sql)
            return c.fetchall()
        except Exception as e:
            print(sql, e)
            return []
        finally:
            if commit:
                self.conn.commit()
            self.conn.close()


class DbConfig(DbBase):
    def __init__(self):
        super(DbConfig, self).__init__("CONFIG")
        if not self.check_table_exist():
            self.init_db()

    def init_db(self):
        """
        初始化本地数据库
        """
        # 创建快捷指令表
        self.execute('''CREATE TABLE {} 
                    ( ID INT PRIMARY KEY     NOT NULL,
                    NAME           TEXT    NOT NULL,
                    COMMAND        TEXT    NOT NULL);'''.format(self.table), commit=True)

    def insert_config(self, name="", command=""):
        """
        插入数据
        :param name: 名称
        :param command: 指令
        :return:
        """
        # 先获取最后一个id
        last_id = self.execute("select ID from {} order by ID desc limit 1;".format(self.table))
        if not last_id:
            last_id = 1
        else:
            last_id = last_id[0][0] + 1
        self.execute("INSERT INTO {} (ID, NAME,COMMAND) VALUES ({}, '{}', '{}')".format(self.table, last_id,
                                                                                        name, command),
                     commit=True)
        return last_id

    def update_config(self, cid, name=None, command=None):
        if name is None and command is None:
            return
        update_comment = ""
        if name is not None:
            update_comment += "NAME = '{}'".format(name)
        if command is not None:
            update_comment += "," if update_comment != "" else ""
            update_comment += "COMMAND = '{}'".format(command)
        self.execute("UPDATE {} set {} where ID={}".format(self.table, update_comment, cid), commit=True)

    def delete(self, cid):
        self.execute("DELETE from {} where ID={};".format(self.table, cid), commit=True)
