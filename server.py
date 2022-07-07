from websocket_server import WebsocketServer
import json
from multiprocessing import Manager
from threading import Thread

from judger import Judger, JudgeResult
from exceptions import JudgeServiceError


class JudgeServer(object):
    def __init__(self):
        self.server = WebsocketServer(host='0.0.0.0', port=8080)
        self.server.set_fn_new_client(self.new_client)
        self.server.set_fn_client_left(self.client_left)
        self.server.set_fn_message_received(self.task_received)

    def start(self):
        self.server.run_forever()

    @staticmethod
    def new_client(client, _server):
        print("New client connected and was given id %d" % client['id'])

    @staticmethod
    def client_left(client, _server):
        print("Client(%d) disconnected" % client['id'])

    def task_received(self, client, _server, message):
        try:
            task = json.loads(message)
        except json.decoder.JSONDecodeError:
            return
        result_queue = Manager().Queue()
        Thread(target=self.feedback, args=(client, result_queue)).start()
        try:
            Judger(task_id=task['task_id'],
                   case_id=task['case_id'],
                   case_conf=task['case_config'],
                   result_queue=result_queue
                   ).judge(task['code'],
                           task['lang'],
                           task['limit'])
        except JudgeServiceError as e:
            result_queue.put(Judger.make_report(
                status=JudgeResult.SYSTEM_ERROR,
                score=0,
                max_time=0,
                max_memory=0,
                log=str(e),
                detail=[]
            ))
        result_queue.put(None)

    def feedback(self, client, queue):
        while True:
            item = queue.get()
            if item is None:
                break
            data = json.dumps(item)
            self.server.send_message(client, data)


server = JudgeServer()
server.start()
