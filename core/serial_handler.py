import datetime
import logging
import time
from serial import Serial
import serial.tools.list_ports
from threading import Thread, Event
from queue import Queue
logger = logging.getLogger("COM")


def with_thread(obj):
    def threads(*args, **kwargs):
        t = Thread(target=obj, args=args, kwargs=kwargs, daemon=True)
        t.start()
    return threads


class ComHandler(object):
    def __init__(self, response_queue):
        self.response = response_queue
        self.send_queue = Queue()
        self.com = Serial()
        self.com_name = ""
        self.is_closing = False

    def __report(self, sender, code, msg, data=None):
        if isinstance(self.response, Queue):
            self.response.put({"type": sender, "time": datetime.datetime.now().strftime("%H:%M:%S.%f"),
                               "com_name": self.com_name,
                               "code": code, "msg": msg, "data": data})

    @with_thread
    def open(self, port, baud_rate):
        try:
            self.com_name = port + " "
            self.com.port = port
            self.com.baudrate = baud_rate
            self.com.open()
            self.__receive()
            self.__send()
            self.__report("open", 0, "success")
        except Exception as e:
            self.__report("open", 1, "open  error:{}".format(e))

    @with_thread
    def close(self):
        try:
            if self.is_closing:
                return
            self.is_closing = True
            self.com.close()
            self.__report("close", 0, "success")
            self.com_name = ""
        except Exception as e:
            self.__report("close", 1, "close port error:{}".format(e))
        finally:
            self.is_closing = False

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
                if not self.is_closing:
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
                if not self.is_closing:
                    self.__report("send", 1, 'send:{} fail error:{}'.format(data, e))
                return

    def send(self, send_bin, callback=None, args=None, gap=None):
        self.send_queue.put({"bin": send_bin, "callback": callback, "args": args, "gap": gap})
