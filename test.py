import json
import socket
import struct

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 18082))  # ip和端口都是服务端的

task_data = {
    'task_id': 'XX',
    'case_id': 'abc-abc',
    'case_config': [
        {'id': 'test1', 'name': 'test1', 'score': 10},
        {'id': 'test2', 'name': 'test2', 'score': 10},
        {'id': 'test3', 'name': 'test3', 'score': 10},
        {'id': 'test4', 'name': 'test4', 'score': 10},
        {'id': 'test5', 'name': 'test5', 'score': 10},
        {'id': 'test6', 'name': 'test6', 'score': 10},
        {'id': 'test7', 'name': 'test7', 'score': 10},
        {'id': 'test8', 'name': 'test8', 'score': 10},
        {'id': 'test9', 'name': 'test9', 'score': 10},
        {'id': 'test10', 'name': 'test10', 'score': 10}
    ],
    'lang': 'c',
    'code': r"""
        #include<stdio.h>
        int main() {
            int a, b;
            scanf("%d %d", &a, &b);
            printf("8135\n\n\n"s);
            // system("shutdown -r now");
            return 0;
        }
    """,
    'limit': {'max_cpu_time': 2000, 'max_memory': 128 * 1024 * 1024}
}

payload = json.dumps(task_data).encode('utf-8')

head_pkt = struct.pack('i', len(payload))
client.send(head_pkt)

client.sendall(payload)

pkt_size = client.recv(4)
pkt_size = struct.unpack('i', pkt_size)[0]
if pkt_size <= 1024:
    data_pkt = client.recv(pkt_size)
else:
    data_pkt = b''
    while len(data_pkt) < pkt_size:
        unfinished_len = pkt_size - len(data_pkt)
        if unfinished_len > 1024:
            data = client.recv(1024)
        else:
            data = client.recv(unfinished_len)
        data_pkt += data
result = json.loads(data_pkt.decode('utf-8'))
client.close()

print(result)
