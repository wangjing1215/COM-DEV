import datetime
import sys
import threading
import time
from serial import Serial
import serial.tools.list_ports
from threading import Thread, Event

from queue import Queue


def with_thread(obj):
    def threads(*args, **kwargs):
        t = threading.Thread(target=obj, args=args, kwargs=kwargs)
        t.start()
    return threads


class ComHandler(object):
    def __init__(self, response_queue):
        self.response = response_queue
        self.send_queue = Queue()
        self.com = Serial()

    def __report(self, sender, code, msg, data=None):
        if isinstance(self.response, Queue):
            self.response.put({"type": sender, "time": datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S.%f"),
                               "code": code, "msg": msg, "data": data})

    @with_thread
    def open(self, port, baud_rate):
        try:
            self.com.port = port
            self.com.baudrate = baud_rate
            self.com.open()
            self.__receive()
            self.__send()
            self.__report("open", 0, "success")
        except Exception as e:
            self.__report("open", 1, "open com error:{}".format(e))

    @with_thread
    def close(self):
        try:
            self.com.close()
            self.__report("close", 0, "success")
        except Exception as e:
            self.__report("close", 1, "close port error:{}".format(e))


    @with_thread
    def search(self, *args):
        self.__report("search", 0, 'success', serial.tools.list_ports.comports())

    @with_thread
    def __receive(self):
        while True:
            try:
                if self.com.in_waiting:
                    res = self.com.read(self.com.in_waiting)
                    self.__report("receive", 0, 'success', res)
            except Exception as e:
                self.__report("receive", 1, "receive error:{}".format(e))
                return

    @with_thread
    def __send(self):
        # data {"bin": b"123", "after_fun": fun object, "args": (1, ), "gap": 48}
        while True:
            if self.com.out_waiting:
                continue
            data = self.send_queue.get()
            try:
                start = time.time()
                self.com.write(data["bin"])
                self.__report("send", 0, 'success', {"bin": data["bin"],
                                                     "fun": data["callback"],
                                                     "args": data.get("args", ())})
                end = time.time()
                if "gap" in data.keys() and data["gap"] is not None and data["gap"]/1000 > (end - start):
                    # ms
                    Event().wait(data["gap"]/1000 - end + start)
            except Exception as e:
                self.__report("send", 1, 'send:{} fail error:{}'.format(data, e))
                return

    def send(self, send_bin, callback=None, args=None, gap=None):
        self.send_queue.put({"bin": send_bin, "callback": callback, "args": args, "gap": gap})


if __name__ == "__main__":
    wait_queue = Queue()
    com = ComHandler(wait_queue)
    # com.search()
    com.open("COM4", 9600)
    a = 1
    while True:
        # print(wait_queue.get())
        com.send("send：{}".format(a).encode(), gap=48)
        a += 1


