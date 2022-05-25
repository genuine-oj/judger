import socketserver
import json
import struct
import signal
from multiprocessing import Manager
from threading import Thread, Event

from judger import Judger, JudgeResult
from exceptions import JudgeServiceError

quit_event = Event()


def quit_server(signal, frame):
    quit_event.set()


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            pkt_size = struct.unpack('i', self.request.recv(4))[0]
            if pkt_size <= 1024:
                test_data_pkt = self.request.recv(pkt_size)
            else:
                test_data_pkt = b''
                while len(test_data_pkt) < pkt_size:
                    unfinished_len = pkt_size - len(test_data_pkt)
                    if unfinished_len > 1024:
                        data = self.request.recv(1024)
                    else:
                        data = self.request.recv(unfinished_len)
                    test_data_pkt += data
            test_data = json.loads(test_data_pkt.decode('utf-8'))
            result_queue = Manager().Queue()
            Thread(target=self.feedback, args=(result_queue,)).start()
            try:
                Judger(task_id=test_data['task_id'],
                       case_id=test_data['case_id'],
                       case_conf=test_data['case_config'],
                       result_queue=result_queue
                       ).judge(test_data['code'],
                               test_data['lang'],
                               test_data['limit'])
            except JudgeServiceError:
                result_queue.put(Judger.make_report(
                    status=JudgeResult.SYSTEM_ERROR,
                    score=0,
                    max_time=0,
                    max_memory=0,
                    log='Judge Server Error',
                    detail=[]
                ))
        except ConnectionResetError:
            pass

    def feedback(self, queue):
        item = queue.get()
        data = json.dumps(item).encode('utf-8')
        self.send_chuck(data)
        self.request.recv(1)  # ack

    def send_chuck(self, data):
        head_pkt = struct.pack('i', len(data))
        self.request.sendall(head_pkt)
        self.request.sendall(data)


if __name__ == "__main__":
    HOST, PORT = '0.0.0.0', 18082
    server = socketserver.ThreadingTCPServer((HOST, PORT), RequestHandler)
    print(f'OJ Judger started on {HOST}:{PORT}, press Ctrl-C to exit.')
    signal.signal(signal.SIGINT, quit_server)
    signal.signal(signal.SIGTERM, quit_server)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    quit_event.wait()
    print('Exiting...')
    server.shutdown()
    server.server_close()
