import socket
import os 
import struct

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
        try:
            buf = b''
            while len(buf) < 4:  # Assuming the integer is 4 bytes long
                data = conn.recv(4 - len(buf))
                if not data:
                    return None
                buf += data
            num = struct.unpack('!I', buf)[0]  # Network byte order (big-endian)
            return num
        except Exception as e:
            print(f"Error receiving int: {e}")
            return None


    def receive_string(self, conn):
        try:
            string_size = self.receive_int(conn)
            if string_size is None:
                return None

            buf = b''
            while len(buf) < string_size:
                data = conn.recv(min(Server.buffer_size, string_size - len(buf)))
                if not data:
                    return None
                buf += data

            return buf.decode()
        except Exception as e:
            print(f"Error receiving string: {e}")
            return None
      
      
    def receive_file(self, conn, dir_path):
        """
        Returns filename received
        """
        try:
            file_size = self.receive_int(conn)
            if file_size is None:
                return None
            filename_size = self.receive_int(conn)
            if filename_size is None:
                return None
            filename = conn.recv(filename_size).decode()
            if not filename:
                print("Filename not received.")
                return None

            filename = os.path.basename(filename)  # Convert abs path to just the file name

            # Ensure the directory path ends with a separator
            dir_path = os.path.join(dir_path, filename).replace('\\', '/')
            # 'wb' mode ensures that an existing file will be overwritten by the newly sent file
            with open(dir_path, 'wb') as file:
                remaining_size = file_size
                while remaining_size > 0:
                    data = conn.recv(min(Server.buffer_size, remaining_size))
                    if not data:
                        print("Client disconnected during file transfer.")
                        return None
                    file.write(data)
                    remaining_size -= len(data)
            return filename
        except Exception as e:
            print(f"Error receiving file: {e}")
            try:
                conn.sendall("Failed to receive file.".encode())
            except:
                pass
            return None  


    def _utf8len(self, s):
        return len(s.encode('utf-8'))



    def _send_int(self, conn, n):
        """
        Function for sending server acknowledgement to client
        """
        # Pack the integer as a 4-byte big-endian format
        val = struct.pack('!I', n)
        conn.sendall(val)


    # send a single string s to server 
    def _send_string(self, conn, s):
        """
        Function for sending server acknowledgement to client
        """
        if not self.client_socket:
            print("Client not connected.")
        
        try:
            self.send_int(conn, self._utf8len(s))        # send the length of s in bytes
            conn.sendall(s.encode())
        except Exception as e:
            print(f"Error sending server acknolwedgement: {e}")   
    

    def _send_server_ack(self, conn, msg):
        try:
            s = f"Server acknowledgement: {msg}"
            print(s)
            self._send_string(conn, s)
        except Exception as e:
            print(f"Error sending server acknolwedgement: {e}")


