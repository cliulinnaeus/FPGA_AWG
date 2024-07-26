import socket
import os 


class Server():
    host = '0.0.0.0'
    port = 8080
    buffer_size = 4096    
    
    def __init__(self, ):
        self.is_running = False  
    
    

    def shutdown_server(self):
        if self.server_socket:
            self.server_socket.close()
            print(f"Server at port {Server.port} has been shut down.")
            self.is_running = False


    # To be overwritten by a child class
    def run_server(self):
        """
        Start the server and wait for connection
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((Server.host, Server.port))
        self.server_socket.listen()
        self.is_running = True
        print(f"Server listening on port {Server.port}...")
        
    
    def receive_int(self, conn):
        buf = ''
        sep = '\n'
        while sep not in buf:
            buf += conn.recv(1).decode()
        num = int(buf)
        return num

    
    def receive_string(self, conn):
        try:
            string_size = self.receive_int(conn)
            remaining_size = string_size
            buf = ''
            while True:
                if remaining_size > Server.buffer_size:
                    data = conn.recv(Server.buffer_size)
                    if not data:
                        break
                    data_size = len(data)
                    remaining_size = remaining_size - data_size
                else:
                    data = conn.recv(remaining_size)
                    buf += data.decode()
                    break
                buf += data.decode()
            return buf        
        except Exception as e:
            print(f"Error receiving string: {e}")
            conn.sendall("Failed to receive string.".encode()) 
        
    
    def receive_file(self, conn, dir_path):
        try:
            file_size = self.receive_int(conn)
            filename_size = self.receive_int(conn)
            filename = conn.recv(filename_size).decode()
            remaining_size = file_size

            if not filename:
                print("Filename not received.")
                return
            # Ensure the directory path ends with a separator
            if not dir_path.endswith(os.path.sep):
                dir_path += os.path.sep

            # 'wb' mode ensures that an existing file will be overwritten by the newly sent file
            with open(dir_path + filename, 'wb') as file:
                while True:
                    if remaining_size > Server.buffer_size:
                        data = conn.recv(Server.buffer_size)
                        if not data:
                            break
                        data_size = len(data)
                        remaining_size = remaining_size - data_size
                    else:
                        data = conn.recv(remaining_size)
                        file.write(data)
                        break
                    file.write(data)
            conn.sendall("File received successfully.".encode())
        except Exception as e:
            print(f"Error receiving file: {e}")
            conn.sendall("Failed to receive file.".encode()) 



