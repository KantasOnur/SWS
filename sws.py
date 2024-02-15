import os.path
import select
import socket
import sys
import queue
from datetime import datetime
import re

UNIXNEWLINE = '\n'
WINDOWSNEWLINE = '\r\n'

MSG_MAP = {200: 'OK', 404: 'Not Found', 400: 'Bad Request'}


def closeWorker(sockets_list, readable, worker, timestamp, outputs):
    worker.close()
    # if worker in outputs:
    # print(len(sockets_list), len(outputs))
    outputs.remove(worker)
    # if worker in sockets_list:
    sockets_list.remove(worker)
    # print(len(sockets_list), len(outputs))
    # readable.remove(worker)
    if worker in timestamp:
        del timestamp[worker]


def is_persistant(connection_type):
    if connection_type is not None:
        return re.search("\n?Connection:( )*keep-alive( )*\n?", connection_type, re.IGNORECASE) is not None
    return None


def process(request):
    match = re.match(r"(GET /(.*) HTTP/1\.0)(\n)?((\n?(.*))*)?", request)
    if match:
        connection_type = is_persistant(match.group(4))
        return True, match.group(2), connection_type, match.group(1)

    return False, None, None, request[:-1]


def process_response(whole_message, file, is_persistant, time, msg):
    response = f"HTTP/1.0 {msg} {MSG_MAP[msg]}\r\nConnection: {'keep-alive' if is_persistant else 'close'}\r\n\r\n"
    if msg == 200:
        with open(file, 'r') as contents:
            response += contents.read()
    return response


def main():
    server_address = (sys.argv[1], int(sys.argv[2]))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind(server_address)
    server.listen(5)
    timestamp = {}
    request_time = {}

    sockets_list = [server]
    outputs = []
    request_messages = {}
    response_messages = {}
    client_location = {}
    whole_messages = {}
    while True:

        for worker in timestamp:
            if abs(timestamp[worker] - datetime.now().astimezone()).seconds > 30:
                closeWorker(sockets_list, readable, worker, timestamp, outputs)
                break

        readable, writable, exceptional = select.select(sockets_list, outputs, sockets_list, 25)

        if not readable and not writable and not exceptional:
            sys.exit()

        for s in readable:
            if s == server:
                client_socket, client_address = server.accept()
                sockets_list.append(client_socket)
                client_location[client_socket] = f"{client_address[0]}:{client_address[1]}"
            else:
                message = s.recv(1024).decode()
                if message:
                    if s in request_messages:
                        request_messages[s] += message
                    else:
                        request_messages[s] = message

                if len(message) < 1024 and message:
                    response_queue = queue.Queue()
                    requests = [i for i in request_messages[s].replace(WINDOWSNEWLINE, UNIXNEWLINE).split('\n\n') if
                                i not in ('', '\n')]


                    for request in requests:
                        valid, file, persistant, input_request = process(request)
                        if not valid:
                            response_queue.put((400, None, input_request, "error"))
                            break
                        else:
                            if os.path.exists(file):
                                response_queue.put((200, persistant, input_request, file))
                            else:
                                response_queue.put((404, persistant, input_request, file))

                    if request_messages[s][-2:] in (WINDOWSNEWLINE * 2, UNIXNEWLINE * 2) or (
                    400, None, input_request, "error") in response_queue.queue:
                        timestamp[s] = datetime.now().astimezone()
                        if not request_messages[s] == '\n\n':
                            request_time[s] = timestamp[s]
                            if s not in outputs:
                                outputs.append(s)
                            response_messages[s] = response_queue
                            whole_messages[s] = request_messages[s]
                        request_messages[s] = ''

        for s in writable:

            try:
                next_msg, is_persistant, input_request, file = response_messages[s].get_nowait()
            except queue.Empty:
                if not is_persistant:
                    closeWorker(sockets_list, readable, s, timestamp, outputs)
            else:
                time = request_time[s].strftime("%a %b %d %H:%M:%S %Z %Y")
                print(f"{time}: {client_location[s]} {input_request if input_request != 'error' else ''}; HTTP/1.0 {next_msg} {MSG_MAP[next_msg]}")
                response = process_response(whole_messages[s], file, is_persistant, request_time[s], next_msg)
                s.send(response.encode())

                if not is_persistant or next_msg == 400:
                    closeWorker(sockets_list, readable, s, timestamp, outputs)


if __name__ == "__main__":
    main()
