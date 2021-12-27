import time
from PyQt5.QtCore import QObject, pyqtSignal
from threading import Thread, Lock
from core.logger import logger


class Dealer(QObject):
    msg = pyqtSignal(bytes)

    def __init__(self, receive_queue):
        super(Dealer, self).__init__()
        self.receive_queue = receive_queue
        self.com_str = b""
        self.err_str = b""
        self.com_lock = Lock()
        # 是否开启报文拼接
        self.is_start = False
        # 大小端
        self.endian = 0
        # 报文头部
        self.head = (b"LC", b"BC", b"RC")
        # 报文长度字节所在位置
        self.len_position = 2, 4
        # 报文长度字节 + 附加字节 == 报文全长
        self.add_len = 4
        # 等待时长 一次为0.01s
        self.wait_count = 10
        Thread(target=self.__receive, daemon=True, name="Receive").start()
        Thread(target=self.package_contain, daemon=True, name="PackageContain").start()

    def set_head(self, input_str):
        try:
            res = input_str.split(",")
            self.head = tuple([i.encode() for i in res])
            logger.info("set head:{}".format(self.head))
        except Exception as e:
            logger.error("parse error:{}".format(e))

    def set_len(self, input_str):
        try:
            res = input_str.split(":")
            self.len_position = tuple([int(i) for i in res])
            logger.info("set head:{}".format(self.len_position))
        except Exception as e:
            logger.error("parse error:{}".format(e))

    def __receive(self):
        while True:
            data = self.receive_queue.get()
            if self.is_start:
                self.com_lock.acquire()
                self.com_str += data
                self.com_lock.release()
            else:
                self.report(data, 2)

    def package_contain(self):
        wait_count = 0
        while True:
            if self.com_str != b"":
                index = 0
                deal_len = len(self.com_str)
                while index < deal_len:
                    # 小于2个字节 无法判断头部 跳出循环等待后续字节
                    if deal_len < 2:
                        break
                    # 头部不符合的情况下 偏移一个字节
                    if not self.com_str[index:].startswith(self.head):
                        self.err_str += self.com_str[index:index+1]
                        index += 1
                        continue
                    length = self.com_str[index:][self.len_position[0]:self.len_position[1]]
                    if self.endian:
                        length = length[::-1]
                    # 当前报文不满足获取长度字节 跳出循环等待后续字节
                    if len(length) < self.len_position[1] - self.len_position[0]:
                        break
                    num_length = int(length.hex(), 16)
                    # 当前报文不满足获取整体报文 跳出循环等待后续字节
                    current_len = len(self.com_str[index:])
                    if current_len < num_length + self.add_len:
                        if wait_count == 0:
                            logger.info("wish len:{} current len:{}".format(num_length + self.add_len, current_len))
                        break
                    else:
                        # 获取到正确报文 上报
                        end_position = index + num_length + self.add_len
                        self.report(self.com_str[index:end_position], 0)
                        index = end_position
                if index > 0:
                    self.com_lock.acquire()
                    self.com_str = self.com_str[index:]
                    self.com_lock.release()
                    wait_count = 0
                else:
                    time.sleep(0.01)
                    wait_count += 1
                # 超过10次index连续为0 将self.com_str清空
                if wait_count > self.wait_count:
                    wait_count = 0
                    self.report(self.com_str[index:index + deal_len], 1)
                    self.com_lock.acquire()
                    self.com_str = self.com_str[deal_len:]
                    self.com_lock.release()
            else:
                # 当前没有报文 如果存在错误报文 也需吐出
                self.report(b"", 1)
                time.sleep(0.01)

    def report(self, package, contain_flag):
        # 拼接成功的情况下 先吐出错误报文 不成功地情况下 一起吐出 并置空错误拼接字符串
        if contain_flag == 0:
            if self.err_str != b"":
                self.msg.emit(self.err_str)
                logger.info("[CONTAIN_ERR]len:{} data:{}".format(len(self.err_str), self.err_str))
                self.err_str = b""
            self.msg.emit(package)
            logger.info("[CONTAIN_SUCCESS]len:{} data:{}".format(len(package), package))
        elif contain_flag == 1:
            res_str = self.err_str + package
            if res_str:
                self.msg.emit(res_str)
                self.err_str = b""
                logger.info("[CONTAIN_ERR] len:{} data:{}".format(len(res_str), res_str))
        else:
            self.msg.emit(package)
            logger.info("[CONTAIN_IGNORE] len:{} data:{}".format(len(package), package))
