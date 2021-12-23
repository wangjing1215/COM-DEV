import json
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

    def select_all(self, add_sql=""):
        sql = "select * from {} {};".format(self.table, add_sql)
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

    def get_next_id(self):
        # 先获取最后一个id
        last_id = self.execute("select ID from {} order by ID desc limit 1;".format(self.table))
        if not last_id:
            last_id = 1
        else:
            last_id = last_id[0][0] + 1
        return last_id

    def delete(self, cid):
        self.execute("DELETE from {} where ID={};".format(self.table, cid), commit=True)


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
                    CATEGORY       CHAR(64),
                    NAME           CHAR(64),
                    COMMAND        TEXT      NOT NULL,
                    IS_HEX         SMALLINT  NOT NULL);'''.format(self.table), commit=True)

    def insert_config(self, category="", name="", command="", is_hex=0):
        """
        插入数据
        :param category: 类别
        :param name: 名称
        :param command: 指令
        :param is_hex: 是否以16进制字符串发送
        :return:
        """
        # 先获取最后一个id
        last_id = self.get_next_id()
        self.execute("INSERT INTO {} (ID, CATEGORY, NAME,COMMAND, is_hex)  \
        VALUES ({}, '{}', '{}', '{}', {})".format(self.table, last_id, category, name, command, is_hex), commit=True)
        return last_id

    def update_config(self, cid, category=None, name=None, command=None, is_hex=None):
        if category is None and name is None and command is None and is_hex is None:
            return
        update_comment = ""
        if category is not None:
            update_comment += "CATEGORY = '{}'".format(category)
        if name is not None:
            update_comment += "," if update_comment != "" else ""
            update_comment += "NAME = '{}'".format(name)
        if command is not None:
            update_comment += "," if update_comment != "" else ""
            update_comment += "COMMAND = '{}'".format(command)
        if is_hex is not None:
            update_comment += "," if update_comment != "" else ""
            update_comment += "IS_HEX = {}".format(is_hex)

        self.execute("UPDATE {} set {} where ID={}".format(self.table, update_comment, cid), commit=True)

    def get_category(self):
        """
        获取所有类目
        :return:
        """
        return self.execute("select distinct(CATEGORY) from {}".format(self.table))


class SysConfig(DbBase):
    def __init__(self):
        super(SysConfig, self).__init__("SYS_CONFIG")
        if not self.check_table_exist():
            self.init_db()

    def init_db(self):
        """
        TYPE: 根据type字段来修改返回格式, 储存格式皆为字符串 如 int str float json
        :return:
        """
        self.execute('''CREATE TABLE {} 
                            (
                            S_KEY   CHAR(64) PRIMARY KEY  NOT NULL,
                            TYPE    CHAR(64),
                            VALUE   TEXT);'''.format(self.table), commit=True)

    def insert(self, key, save_type, value):
        self.execute("INSERT INTO {} (S_KEY, TYPE, VALUE)  \
                VALUES ('{}', '{}', '{}')".format(self.table, key, save_type, value),
                     commit=True)

    def update(self, key=None, value=None, save_type=None):
        if key is None or value is None:
            return
        if self.get_by_key(key) is None:
            # 不存在当前key 就插入一条
            self.insert(key, save_type, value)
        else:
            sql = "value = '{}'".format(value)
            self.execute("UPDATE {} set {} where S_KEY='{}'".format(self.table, sql, key), commit=True)

    def delete(self, key):
        self.execute("delete from {} where S_KEY='{}'".format(self.table, key))

    def get_by_key(self, key):
        res = self.execute("select type, value from {} where S_KEY = '{}'".format(self.table, key))
        if res:
            res_type, value = res[0]
            if res_type == "int":
                return int(value)
            elif res_type == "str":
                return value
            elif res_type == "float":
                return float(value)
            elif res_type == "json":
                return json.loads(value)
            else:
                return value
        return None
