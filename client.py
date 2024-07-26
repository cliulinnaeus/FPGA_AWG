import socket 
import os


class Client():

    buffer_size = 4096
    
    def __init__(self, host, port):
        self.host = host        # 192.168.0.234 by default
        self.port = port        # 8080 by default

    
    # To be deleted
    def connect_and_send_file(self, file_to_send):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((self.host, self.port))
                print(f"Connected to server {self.host} on port {self.port}")
                self.send_file(file_to_send, client_socket) 
        except Exception as e:
            print(f"Error connecting to server: {e}")
    
    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to server {self.host} on port {self.port}")
        except Exception as e:
            print(f"Error connecting to server: {e}") 
    
    def disconnect(self):
        if self.client_socket:
            self.client_socket.close()
            print(f"Disconnected from server at {self.host}:{self.port}")
    
    
    def _utf8len(self, s):
        return len(s.encode('utf-8'))

    def send_int(self, n):
        val = str(n) + '\n'
        self.client_socket.sendall(val.encode())


    # send a single string s to server 
    def send_string(self, s):
        if not self.client_socket:
            raise Exception("Client not connected.")
        
        try:
            self.send_int(self._utf8len(s), s)        # send the length of words in bytes
            self.client_socket.sendall(s.encode())
        except Exception as e:
            print(f"Error sending string: {e}")   

        # response = self.client_socket.recv(4096).decode()
        # print(f"Server response: {response}")
    
        
    def send_file(self, filename):
        file_size = os.stat(filename).st_size
        try:
            self.send_int(file_size, self.client_socket)        # send the size of the file
            self.send_int(len(filename), self.client_socket)    # send the size of filename in bytes
            self.client_socket.sendall(filename.encode())  # send the file name first
            #continuously read and send the file content until EOF
            with open(filename, 'rb') as file:
                while True:
                    bytes_read = file.read(Client.buffer_size)
                    if not bytes_read:
                        break
                    self.client_socket.sendall(bytes_read)
            print("File has been sent.")
            # wait for acknolwdgement
            # this line runs forever waiting for the server to send stuff
            # this line will only block if there's nothing in the socket buffer 
            ack = self.client_socket.recv(Client.buffer_size).decode()
            print(f"Server acknowledgement: {ack}")
        except Exception as e:
            print(f"Error sending file: {e}")

             
        