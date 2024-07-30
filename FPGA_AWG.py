from qick import *
from AWGProgram import *
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
        self.waveform_lst = {}     # list of registered waveforms
        self.envelope_lst = {}     # list of idata and qdata  
        self.program_lst = {}      # the program to be ran

        # register all .json files currently on disk into the above dicts
        self.waveform_lst = self._load_files_to_dict(self.waveform_dir_path)
        self.envelope_lst = self._load_files_to_dict(self.envelope_dir_path)
        self.program_lst = self._load_files_to_dict(self.program_dir_path)


        # start self.server on listening mode
        self.set_state("listening")   # does nothing other than indicating the status. SET_TO_LISTENING_STATUS() only from "starting"
                                      # or firing status
        
        # load the programming logic onto FPGA
        self.soc = QickSoc()
        self.soccfg = self.soc
        self.awg_prog = None         # AWGProgram to be created during compilation


        # start the server for listening, state will be set to listening
        # TODO: combine everything into start server, the server should set up when 
        # instantiated, then when calling start_server() then it should be ready to listen to 
        # connections and process commands 
        # self.run_server()                # start the server and let it listen for client connections
                

    def _load_files_to_dict(self, directory_path):
        """
        Helper function to load json files from a directory into a dictionary.
        Ensures that two json files with the same "name" subfield will be overwritten in the dict.
        Returns a dict containing all json files stored in current directory_path
        """
        file_dict = {}
        if os.path.exists(directory_path):
            for filename in os.listdir(directory_path):
                if filename.endswith('.json'):  # Check if the file is a .json file
                    file_path = os.path.join(directory_path, filename).replace('\\', '/')  # Ensure the path uses forward slashes
                    if os.path.isfile(file_path):
                        name = self._read_file_name(file_path)
                        file_dict[name] = file_path
        return file_dict


    def _read_file_name(self, file_path):
        """
        Helper function to read "name" field in the json file FILE_PATH
        """
        with open(file_path, 'rb') as file:
            data = json.load(file)
            name = data["name"]
        return name



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

        # bind server to server port    
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
                            self.stop_program()

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
        
        
    @property
    def get_waveform_lst(self):
        return self.waveform_lst
    
    @property
    def get_envelope_lst(self):
        return self.envelope_lst
       
    @property
    def get_program_lst(self):
        return self.program_lst
       
    @property
    def get_state(self):
        return self.state
    
    def set_state(self, state):
        """
        set the AWG into server listening mode or firing mode 
        """        
        self.state = state
    


    def _update_json_file(self, file_path, new_name):
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r+') as json_file:
                    data = json.load(json_file)
                    if data.get("name") != new_name:
                        data["name"] = new_name
                        json_file.seek(0)
                        json.dump(data, json_file, indent=4)
                        json_file.truncate()
        except Exception as e:
            print(f"Error updating JSON file: {e}")


    def upload_waveform_cfg(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return 
        name = self.receive_string(conn)
        # if the name here and the name in json are different, replace the name in json by the name given

        filename = self.receive_file(conn, FPGA_AWG.waveform_dir_path)            # save the config file to disk; filename does not contain abs path
        file_path = os.path.join(FPGA_AWG.waveform_dir_path, filename).replace('\\', '/')
        # if name is not equal to json file's name field, update the json name 
        self._update_json_file(file_path, name)                 
        self.waveform_lst[name] = file_path
        msg = "File received successfully."
        self._send_server_ack(conn, msg)
    

    def upload_envelope_data(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return 

        name = self.receive_string(conn)
        filename = self.receive_file(conn, FPGA_AWG.envelope_dir_path)
        file_path = os.path.join(FPGA_AWG.envelope_dir_path, filename).replace('\\', '/')
        self._update_json_file(file_path, name)    
        self.envelope_lst[name] = file_path
        msg = "Files received successfully."
        self._send_server_ack(conn, msg)


    # upload the program config 
    def upload_program(self, conn):
        if self.state != "listening":
            msg = f"Can't receive file: current AWG state is {self.state}."
            self._send_server_ack(conn, msg)
            return
        
        name = self.receive_string(conn)
        filename = self.receive_file(conn, FPGA_AWG.program_dir_path)
        file_path = os.path.join(FPGA_AWG.program_dir_path, filename).replace('\\', '/')
        self._update_json_file(file_path, name)                 
                 
        self.program_lst[name] = file_path
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
                path = os.path.join(FPGA_AWG.waveform_dir_path, self.waveform_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.waveform_lst.pop(name)
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
                path = os.path.join(FPGA_AWG.envelope_dir_path, self.envelope_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.envelope_lst.pop(name)
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
                path = os.path.join(FPGA_AWG.program_dir_path, self.program_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.program_lst.pop(name)
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
            msg = f"trig_mode can only be 'internal' or 'external'."
            self._send_server_ack(conn, msg)
            return     
        self.trig_mode = trig_mode
        msg = f"Trigger mode is successfully set to {trig_mode}."
        self._send_server_ack(conn, msg)
        # TODO: set the trigger mode for AWGProgram


            
    def set_to_firing_state(self):
        if self.state != "listening":
            raise Exception(f"Switch state failed: trying to switch to firing state when current state is {self.state}")
        self.server.stop()
        self.set_state("firing")
        # instantiate AWGProgram, connect to FPGA's tproc and wait for configurating registers and pulse envelopes
        
        # TODO: need to write a parser for self.config from commands 
        # TODO: how to write multiple waveforms? 
        if not self.awg_prog: 
            self.awg_prog = AWGProgram(self.soccfg, self.config)         # instantiate Qick AWGProgram
        print("Switched to firing state.")
        self.awg_prog.config_all(self.soc)                               # load parameters into registers, load waveform data to PL memory
        print("Finished loading pulse parameters to registers and waveform data to memory.")
        self.soc.start_src(self.trig_mode)                          # set trigger mode for the tproc. "internal" or "external"
        print(f"Trigger mode is set to: {self.trig_mode}\n")
        print("-----------------------ready to fire pulse---------------------------")



    def set_to_listening_state(self):
        if self.state != "firing" or self.state != "starting":
            raise Exception(f"Switch state failed: trying to switch to listening state when current state is {self.state}")    
        self.set_state("listening")
    

    # how to get rid of the initial delay time when running the program?
    def start_program(self, conn):
        """
        Start the Qick program. At this point, all the registers are already set and envelope memory loaded
        """


        prog_name = self.receive_string(conn)
        # TODO: correctly configure all pulse, compile program, and run

        # find the file with prog_name, read json
        # for program_structure, for each appeared pulse name, search pulse_cfg and generate code to set registers
        # link each pulse to it's respective waveform envelope
        # for program_structure, generate the asm code for the program structure of each channel 

        self.awg_prog = AWGProgram(self.soccfg, self.soc)

        # TODO: write AWGProgram.compile_awg_program(prog_name)
        self.awg_prog.compile_awg_program(prog_name)     # save as an AWGProgram object
        self.awg_prog.config_all(self.soc)               # soc loads all parameters into registers and waveform data into PL memory
        self.soc.start_src(self.trig_mode)               # reset the trigger mode

        self.set_state("firing")                         # to indicate that the server will no longer listen to uploads or deletion        

        self.soc.start_tproc()                           # starts the tproc to run AWGProgram. Pulse will fire when trigger comes in "external" mode
                                                         # or will fire immediately in "internal" mode
        print(f"Program {prog_name} has started...")



    
    def stop_program(self):
        """
        stops currently running program and set output of all generators to 0
        """
        pass

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
    
    

        