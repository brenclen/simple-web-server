import select
import socket
import sys
import queue
import time
import re
import os

class Request:
    def __init__(self,head="", url="", conn="Connection: closed"):
        self.header = head
        self.connection = conn
        self.url = url


class SimpleWebServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        self.serverPort = int(sys.argv[2])
        self.ip = sys.argv[1]
        self.server_address = (self.ip, self.serverPort) ########asdkalsdl###
        print(f'starting up on {self.ip} port {self.serverPort}')
        self.server.bind(self.server_address)

        # Listen for incoming connections
        self.server.listen(5)

        # Sockets from which we expect to read
        self.inputs = [self.server]

        # Sockets to which we expect to write
        self.outputs = []

        # Outgoing message queues (socket:Queue)
        self.message_queues = {}

        # request message
        self.request_message = {}
        self.socket_status = {}
        self.timeout_status = {}

        self.ok = "HTTP/1.0 200 OK\r\n"
        self.notFound = "HTTP/1.0 404 Not Found\r\n"
        self.badRequest = "HTTP/1.0 400 Bad Request\r\n"


        self.timeout = 30

        while self.inputs:
            self.__timeout_checker__()
            self.readable, self.writable, self.exceptional = select.select(self.inputs,
                                                                            self.outputs,
                                                                            self.inputs,
                                                                            self.timeout)
            self.__incoming__()
            self.__outgoing__()

    #timeout sockets that have been inactive for 30s
    def __timeout_checker__(self):
        for sock in list(self.timeout_status):
            if (time.time()-self.timeout_status[sock]) > self.timeout:
                self.__remove_socket__(sock)
                self.timeout_status.pop(sock)

    #iterate over sockets waiting to be heard from
    def __incoming__(self):
        for sock in self.readable:
            if sock is self.server:
            # A "readable" socket is ready to accept a connection
                self.connection, self.client_address = sock.accept()
                self.connection.setblocking(0)
                self.inputs.append(self.connection)
                self.request_message[self.connection] = ""
                # Give the connection a queue for data
                # we want to send
                self.message_queues[self.connection] = queue.Queue()
            else:
                message1 =  sock.recv(1024).decode()
                if message1:
                    self.__process_message__(sock, message1)
                # handle the situation where no messages receive
                

    #iterate over sockets waiting for responses
    def __outgoing__(self):
        for sock in self.writable:
            try:
                msgQueue = self.message_queues[sock]
            except queue.Empty:
            # No messages need to be sent so stop watching
                self.outputs.remove(sock)
                if sock not in self.inputs:
                    sock.close()
                    del self.message_queues[sock]
                    del self.request_message[sock]
            else:
                #print logs and send messages
                while not msgQueue.empty():
                    self.__send_client__(sock, msgQueue.get())
                if sock in self.socket_status:
                    if self.socket_status[sock] == "REMOVE":
                        self.request_message[sock] = ""
                        self.__remove_socket__(sock)
        pass

        #encodes and sends corresponding responses to requests
    def __send_client__(self, sock, req):
        sockname = sock.getsockname()
        stat = self.notFound
        if os.path.isfile("."+req.url):
            f = open("."+req.url, "r")
            contents = f.readlines()
            stat = self.ok
            sock.send(f"{self.ok}{req.connection}\r\n{' '.join(contents)}".encode())
        else:
            sock.send(f"{self.notFound}{req.connection}\r\n".encode())
        print(f"{time.strftime('%a %b %d %H:%M:%S %Z %Y')}: {sockname[0]}:{sockname[1]} {req.header}; {stat}", end = "")
        self.request_message[sock] = ""


    def __exceptions__(self):
        for sock in self.exceptional:
            print('exception condition on', sock.getpeername(),file=sys.stderr)
        # Stop listening for input on the connection
            print(self.inputs)
            self.inputs.remove(sock)
            if sock in self.outputs:
                self.outputs.remove(sock)
                sock.close()
            print(self.inputs)

        # Remove message queue
        del self.message_queues[sock]
        pass

    # tests validity of incoming responses and processes valid ones, responds with error to invalid ones
    def __process_message__(self, sock, message):
        valid = self.__check_validity__(message, sock)
        if valid:
            # if not add the message to the request message for s
            self.request_message[sock] = self.request_message[sock] + message
            mess = self.request_message[sock]
            # check if the end of the requests:
            if mess[-2:] == '\n\n':
            # if it is the end of request, process the request
                self.__process_request__(sock, mess)
            # add the socket s to the output list for watching writability
            if sock not in self.outputs:
                self.outputs.append(sock)
    
    def __check_validity__(self, message, sock):
        typereq = re.match("GET\s/[A-Za-z0-9_-]*(\.|[A-Za-z0-9_-])[A-Za-z0-9_-]*\sHTTP/1.0", message)
        ifCon = re.match("Connection:\s?(keep-alive|closed)", message, re.IGNORECASE)
        if (typereq == None) and (ifCon == None) and (message!='\n'):
            valid = False
            sock.send(self.badRequest.encode())
            sockname = sock.getsockname()
            stat = self.badRequest
            print(f"{time.strftime('%a %b %d %H:%M:%S %Z %Y')}: {sockname[0]}:{sockname[1]} {message.rstrip()}; {stat}", end = "")
            self.__remove_socket__(sock)
        else:
            valid = True
            
        return valid
            

    # adds response messages to be ready to write through my own class of 'Response' as well as figuring out wether to keep connection open or not
    def __process_request__(self, sock, mess):
        temp = mess.split("\n")
        self.socket_status[sock] = "REMOVE"
        for i,line in enumerate(temp):
            if len(temp) > (i+1) and re.match("GET\s/[A-Za-z0-9_-]*(\.|[A-Za-z0-9_-])[A-Za-z0-9_-]*\sHTTP/1.0", line):
                #if its a request line
                matchobj = re.search("/[A-Za-z0-9_-]*(\.|[A-Za-z0-9_-])[A-Za-z0-9_-]*", line)
                status = "Connection: closed"
                try:
                    tempUrl = matchobj.group(0).rstrip()
                except:
                    tempUrl = ""
                if re.match("Connection:\s?keep-alive", temp[i+1], re.IGNORECASE):
                    status = "Connection: keep-alive"
                    self.socket_status[sock] = "KEEP"
                else:
                    status = "Connection: closed"
                newReq = Request(line, tempUrl, status)
                self.timeout_status[sock] = time.time()
                self.message_queues[sock].put(newReq)
        return
    
    #removes sockets from reading and writing
    def __remove_socket__(self, sock):
        if sock in self.inputs:
            self.inputs.remove(sock)
        if sock in self.outputs:
            self.outputs.remove(sock)
        try:
            self.message_queues.remove(sock)
        except:
            pass
        sock.close()
        return



def main():
    sws = SimpleWebServer()

main()