import socket 
import os
import struct 


class Client():

    buffer_size = 4096
    
    def __init__(self):
        self.host = None        # 192.168.0.234 by default
        self.port = None        # 8080 by default

    
    def connect(self, host, port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.host = host
            self.port = port
            print(f"Connected to server {host} on port {port}")
        except Exception as e:
            print(f"Error connecting to server: {e}") 
    
    def disconnect(self):
        if self.client_socket:
            self.client_socket.close()
            print(f"Disconnected from server at {self.host}:{self.port}")
    
    
    def _utf8len(self, s):
        return len(s.encode('utf-8'))


    def send_int(self, n):
        # Pack the integer as a 4-byte big-endian format
        val = struct.pack('!I', n)
        self.client_socket.sendall(val)



    # send a single string s to server 
    def send_string(self, s):
        if not self.client_socket:
            raise Exception("Client not connected.")
        
        try:
            self.send_int(self._utf8len(s))        # send the length of words in bytes
            self.client_socket.sendall(s.encode())
        except Exception as e:
            print(f"Error sending string: {e}")   


    def send_file(self, filename):
        file_size = os.stat(filename).st_size
        try:
            self.send_int(file_size)        # send the size of the file
            self.send_int(len(filename))    # send the size of filename in bytes
            self.client_socket.sendall(filename.encode())  # send the file name first
            #continuously read and send the file content until EOF
            with open(filename, 'rb') as file:
                while True:
                    bytes_read = file.read(Client.buffer_size)
                    if not bytes_read:
                        break
                    self.client_socket.sendall(bytes_read)
            print("File has been sent.")

        except Exception as e:
            print(f"Error sending file: {e}")


    def _receive_int(self):
        try:
            buf = b''
            while len(buf) < 4:  # Assuming the integer is 4 bytes long
                data = self.client_socket.recv(4 - len(buf))
                if not data:
                    return None
                buf += data
            num = struct.unpack('!I', buf)[0]  # Network byte order (big-endian)
            return num
        except Exception as e:
            print(f"Error receiving int: {e}")
            return None

    def _receive_string(self):
        try:
            string_size = self.receive_int()
            if string_size is None:
                return None

            buf = b''
            while len(buf) < string_size:
                data = self.client_socket.recv(min(Client.buffer_size, string_size - len(buf)))
                if not data:
                    return None
                buf += data
            return buf.decode()
        except Exception as e:
            print(f"Error receiving string: {e}")
            return None


    def receive_server_ack(self):
        ack = self._receive_string()
        print(ack)

             
        