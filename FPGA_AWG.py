from qick import *
from AWGProgram import *
from compiler import *
from server import *
import os
import json

class FPGA_AWG(Server):
    
    host = '0.0.0.0'
    port = 8080
    
    waveform_dir_path = "/home/xilinx/FPGA_AWG/waveform_cfg"
    envelope_dir_path = "/home/xilinx/FPGA_AWG/envelope_data" 
    program_dir_path = "/home/xilinx/FPGA_AWG/program_cfg"



    def __init__(self):
        """
        set up the communication and have an server actively listening 
        """
        super().__init__()


        # List of directory paths
        dir_paths = [FPGA_AWG.waveform_dir_path, FPGA_AWG.envelope_dir_path, FPGA_AWG.program_dir_path]
        # Create directories if they don't exist
        for path in dir_paths:
            if not os.path.exists(path):
                os.makedirs(path)
   
        # key: name; value: path to .json
        self.waveform_lst = []     # list of registered waveforms
        self.envelope_lst = []     # list of idata and qdata  
        self.program_lst = []      # the program to be ran

        # register all .json files currently on disk into the above dicts
        self.waveform_lst = self._load_files_to_lst(self.waveform_dir_path)
        self.envelope_lst = self._load_files_to_lst(self.envelope_dir_path)
        self.program_lst = self._load_files_to_lst(self.program_dir_path)

        # start self.server on listening mode
        self.set_state("listening")   # does nothing other than indicating what AWG is doing

        # initialize FPGA: load the tproc onto FPGA
        self.soc = QickSoc()
        self.soccfg = self.soc
        self.awg_prog = AWGProgram(self.soccfg, self.soc)
        self.trig_mode = "internal"  # defaults this to internal 
        self.compiler = Compiler(self.awg_prog)        
        

    def _load_files_to_lst(self, dir_path):
        """
        Helper function to load json files from a directory into a list.
        Returns a list containing the names of all json files stored in current directory_path
        """
        file_lst = []
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):  # Check if the file is a .json file
                    file_lst.append(os.path.splitext(filename)[0])
        return file_lst


    def run_server(self):
        """
        run indefinitely
        listens to client commands and executes them 
        commands that can be executed in the run loop
        
            UPLOAD_WAVEFORM_CFG(wf_cfg_path, name)    # cfg does not include rep and start time; saves cfg to FPGA disk through ethernet
            UPLOAD_EVELOPE_DATA(idata_path, qdata_path, name, name)
            UPLOAD_PROGRAM(prog_cfg_path, name)       # uploads the AWG program into 
                                                
            prog_cfg = {
                prog_structure: "[X, Y, I, rep(10, [X, Y, I, Z])]",
                env_to_waveform_table: {X: (idata_name, qdata_name), Y: (idata_name, None)}
                name: XY8
            }

            wf_cfg = {
                style:
                freq:
                gain:
                phase:
                phrst:
                stdysel:
                outsel:
                length:
                waveform:
            }

            env_cfg = {
                
            }

            a parser will parse prog_structure into asm code and load it with env data

            I operator can be made by a default function that just does the wait

            DELETE_WAVEFORM_CFG(name)    # remove name from waveform_lst
            DELETE_EVELOPE_DATA(name)    # remove name from data memory, empty data memory and delete evelope file
            SET_TRIGGER_MODE(mode)       # "internal" or "external"
            START_PROGRAM(name)          # switch to running mode, starts the QICK AWGProgram given by name;
                                                  # will only instantiate AWGProgram if self.awg_prog is not None
            STOP_PROGRAM(name)           # stops the AWGProgram if it's running
                                                    # how to actually stop program when Qick is running?

            CHECK_STATUS()               # return state "listening" or "firing". Is this even necessary? it will never be able to return firing
            SET_STATUS(status)           # force set the AWG into "firing pulses" or "waiting for upload" mode
            # how to switch from firing mode back? just directly SET_STATUS()
            # how do you define wf_cfg and prog_cfg? especially prog_cfg? 
           
        """

        # bind server to socket    
        print(f"--------------- Server Starting... ---------------")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((FPGA_AWG.host, FPGA_AWG.port))
        self.server_socket.listen()
        self.is_running = True
        print(f"Server listening on port {FPGA_AWG.port}...")

        # infinite loop to wait for connection 
        while True:
            try:
                conn, addr = self.server_socket.accept()
                print(f"Connected by {addr}")

                # loop to process commands 
                while True:
                    try: 
                        command = self.receive_string(conn)
                        # handle the case where client is disconnected
                        if command is None:
                            break                        
                        
                        # process commands
                        if command == "UPLOAD_WAVEFORM_CFG":
                            self.upload_waveform_cfg(conn)

                        elif command == "UPLOAD_ENVELOPE_DATA":
                            self.upload_envelope_data(conn)

                        elif command == "UPLOAD_PROGRAM":
                            self.upload_program(conn)
                    
                        elif command == "DELETE_WAVEFORM_CFG":
                            self.delete_waveform_config(conn)

                        elif command == "DELETE_ENVELOPE_DATA":
                            self.delete_envelope_data(conn)

                        elif command == "DELETE_PROGRAM":
                            self.delete_program(conn)

                        elif command == "SET_TRIGGER_MODE":
                            self.set_trigger_mode(conn)
                        
                        elif command == "START_PROGRAM":
                            self.start_program(conn)

                        elif command == "STOP_PROGRAM": 
                            self.stop_program(conn)

                        elif command == "GET_WAVEFORM_LIST":
                            self.get_waveform_lst(conn)

                        elif command == "GET_ENVELOPE_LIST":
                            self.get_envelope_lst(conn)
                        
                        elif command == "GET_PROGRAM_LIST":
                            self.get_program_lst(conn)

                        elif command == "GET_STATE":
                            self.get_state(conn)

                        else: 
                            msg = f"Unknown command: {command}"
                            self._send_server_ack(conn, msg)

                    except Exception as e:
                        print(f"Error: {e}")
                        break                   
                
            except Exception as e:
                conn.close()
                print(f"Error: {e}")
            finally:
                conn.close()
                print(f"Connection to {addr} has been closed.")
                print(f"Server listening on port {FPGA_AWG.port}...")
        
        
    def get_waveform_lst(self, conn):
        msg = f"Current waveform list: {self.waveform_lst.__repr__()}"
        self._send_server_ack(conn, msg)
    
    def get_envelope_lst(self, conn):
        msg = f"Current program list: {self.envelope_lst.__repr__()}"
        self._send_server_ack(conn, msg)

    def get_program_lst(self, conn):
        msg = f"Current program list: {self.program_lst.__repr__()}"
        self._send_server_ack(conn, msg)
       
    def get_state(self, conn):
        msg = f"Current state is {self.state}..."
        self._send_server_ack(conn, msg)

    def set_state(self, state):
        """
        set the AWG into listening state or firing state
        """        
        self.state = state
    

    def upload_waveform_cfg(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return 
        name = self.receive_string(conn)
        # filename is not used here 
        filename = self.receive_file(conn, FPGA_AWG.waveform_dir_path, name=name)            # save the config file to disk; filename does not contain abs path

        if name not in self.waveform_lst:
            self.waveform_lst.append(name)                 
        msg = "File received successfully."
        self._send_server_ack(conn, msg)
    

    def upload_envelope_data(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return 

        name = self.receive_string(conn)
        filename = self.receive_file(conn, FPGA_AWG.envelope_dir_path, name=name)

        if name not in self.envelope_lst:
            self.envelope_lst.append(name) 
        msg = "File received successfully."
        self._send_server_ack(conn, msg)


    # upload the program config 
    def upload_program(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return
        
        name = self.receive_string(conn)
        filename = self.receive_file(conn, FPGA_AWG.program_dir_path, name=name)
 
        if name not in self.program_lst:
            self.program_lst.append(name)
        msg = "File received successfully."
        self._send_server_ack(conn, msg)


    def delete_waveform_config(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return

        name = self.receive_string(conn)
        if name not in self.waveform_lst:
            msg = f"{name} is not found in waveform list."
            self._send_server_ack(conn, msg)
        else:
            try:
                path = os.path.join(FPGA_AWG.waveform_dir_path, name + ".json").replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.waveform_lst.remove(name)
                msg = f"{name} is deleted successfully."
                self._send_server_ack(conn, msg)
            except Exception as e:
                msg = f"Error: {e}"
                self._send_server_ack(conn, msg)               


    def delete_envelope_data(self, conn):
        if self.state != "listening":
            msg = f"Can't delete file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return 
        
        name = self.receive_string(conn)
        if name not in self.envelope_lst:
            msg = f"{name} is not found in envelope list."
            self._send_server_ack(conn, msg)
        else:
            try:
                path = os.path.join(FPGA_AWG.envelope_dir_path, name + ".json").replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.envelope_lst.remove(name)
                msg = f"{name} is deleted successfully."
                self._send_server_ack(conn, msg)
            except Exception as e:
                msg = f"Error: {e}"
                self._send_server_ack(conn, msg)
    
    
    def delete_program(self, conn):
        if self.state != "listening":
            msg = f"Can't delete file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return
        
        name = self.receive_string(conn)
        if name not in self.program_lst:
            msg = f"{name} is not found in program list."
            self._send_server_ack(conn, msg)
        else:
            try:
                path = os.path.join(FPGA_AWG.program_dir_path, name + ".json").replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.program_lst.remove(name)
                msg = f"{name} is deleted successfully."
                self._send_server_ack(conn, msg)
            except Exception as e:
                msg = f"Error: {e}"
                self._send_server_ack(conn, msg)
    

    def set_trigger_mode(self, conn):
        if self.state != "listening":
            msg = f"Can't set trigger: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return
        
        trig_mode = self.receive_string(conn)
        if trig_mode != "internal" and trig_mode != "external":
            msg = f"Trigger can only be 'internal' or 'external'."
            self._send_server_ack(conn, msg)
            return     
        self.trig_mode = trig_mode
        msg = f"Trigger is set to {trig_mode}."
        self._send_server_ack(conn, msg)




    # how to get rid of the initial delay time when running the program?
    def start_program(self, conn):
        """
        Start the Qick program. At this point, all the registers are already set and envelope memory loaded
        """

        """
        When start program is called, server switches to the firing mode and the following functions can be ran

        get_state():
            this is simple, just have a second thread func the AWGProgram, and the main thread return state
        stop_program():
            not so simple. When ran, it should prompt the other thread to run stop_program and to back to the listening mode



        External mode: 
            when receives a trigger, it uploads the sweep parameter and pulse
            to do it, at the end of every pulse (at the end of the whole sequence specified by prog_cfg),
            update with mathi the parameter that should be sweeped. I should allow multiple parameters to
            be sweeped, and give the user the option to choose if they just want to sweep one
            to define the sweeped parameter, we should just allow the user to define sweep param in the 
            prog_cfg
            for envelope, I think it is the best to define them in wf_cfg instead of in prog_cfg. Just put
            idata and qdata in the json file.

            Let's say 
        """
        
        prog_name = self.receive_string(conn)
        if prog_name not in self.program_lst:
            msg = f"Program {prog_name} is not found in program list."
            self._send_server_ack(conn, msg)
            return

        # disallows all uploads and deletions and trigger set commands during firing state
        self.set_state("firing")

        # compile program and save asm into self.awg_prog
        # whenever a new program is uploaded, self.awg_prog should be reinit
        print("1")
        self.compiler.compile(prog_name)
        print("2")
        print(self.awg_prog.asm())

        self.awg_prog.config_all(self.soc)               # soc loads all parameters into registers and waveform data into PL memory
        print("3")
        self.soc.start_src(self.trig_mode)               # reset the trigger mode
        print("4")
        self.soc.start_tproc()                           # starts the tproc to run AWGProgram. Pulse will fire when trigger comes in "external" mode
                                                         # or will fire immediately in "internal" mode
        print("5")
        msg = f"Program {prog_name} has started..."
        self._send_server_ack(conn, msg)


    
    def stop_program(self, conn):
        """
        stops currently running program and set output of all generators to 0
        """
        # assumes the FPGA is currently in the listening state
        if self.state != "firing":
            msg = f"FPGA is not firing pulses: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return
        
        # stop all generators
        self.soc.reset_gens()
        # self.soc.stop_tproc()
        # reset awg program
        self.awg_prog = AWGProgram(self.soccfg, self.soc)
        self.set_state("listening")
        msg = f"Program is stopped. Server resumes listening..."
        self._send_server_ack(conn, msg)




    def shutdown(self):
        """
        shut down the AWG program, empty the FPGA memory and instance arrays 
        """
        self.waveform_lst.clear()
        self.envelope_lst.clear()
        self.program_lst.clear()
        self.server.stop()
        self.set_status("shutdown")
        print("AWG shutdown.")
    
    

        