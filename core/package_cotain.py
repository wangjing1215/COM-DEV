import time
from PyQt5.QtCore import QObject, pyqtSignal
from threading import Thread, Lock


class Dealer(QObject):
    msg = pyqtSignal(bytes)

    def __init__(self, receive_queue):
        super(Dealer, self).__init__()
        self.receive_queue = receive_queue
        self.com_str = b""
        self.err_str = b""
        self.com_lock = Lock()
        # 大小端
        self.endian = 0
        # 报文头部
        self.head = (b"LC", b"BC", b"RC")
        # 报文长度字节所在位置
        self.len_position = 2, 4
        # 报文长度字节 + 附加字节 == 报文全长
        self.add_len = 4
        Thread(target=self.__receive, daemon=True).start()
        Thread(target=self.package_contain, daemon=True).start()

    def __receive(self):
        while True:
            data = self.receive_queue.get()
            self.com_lock.acquire()
            self.com_str += data
            self.com_lock.release()

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
                    length = self.com_str[index:][self.len_position[0]:self.len_position[1]]
                    if self.endian:
                        length = length[::-1]
                    # 当前报文不满足获取长度字节 跳出循环等待后续字节
                    if len(length) < 2:
                        break
                    num_length = int(length.hex(), 16)
                    # 当前报文不满足获取整体报文 跳出循环等待后续字节
                    if len(self.com_str[index:]) < num_length + self.add_len:
                        break
                    else:
                        # 获取到正确报文 上报
                        end_position = index + num_length + self.add_len
                        self.report(self.com_str[index:end_position], True)
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
                print(index, wait_count)
                if wait_count > 10:
                    wait_count = 0
                    self.report(self.com_str[index:index + deal_len], False)
                    self.com_lock.acquire()
                    self.com_str = self.com_str[deal_len:]
                    self.com_lock.release()
            else:
                # 当前没有报文 如果存在错误报文 也需吐出
                self.report(b"", False)
                time.sleep(0.01)

    def report(self, package, contain_success):
        # 拼接成功的情况下 先吐出错误报文 不成功地情况下 一起吐出 并置空错误拼接字符串
        if contain_success:
            if self.err_str != b"":
                self.msg.emit(self.err_str)
                self.err_str = b""
            self.msg.emit(package)
        else:
            res_str = self.err_str + package
            if res_str:
                self.msg.emit(res_str)
                self.err_str = b""
