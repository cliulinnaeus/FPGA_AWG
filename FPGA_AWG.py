from qick import *
from AWGProgram import *
from server import *
import os
import json

class FPGA_AWG(Server):
    
    waveform_dir_path = ""    # TODO: put in abs path for saving the program data; 
    envelope_dir_path = "" 
    program_dir_path = ""



    def __init__(self):
        """
        set up the communication and have an server actively listening 
        """
        # file_path is the directory that saves all waveform, program, and envelope files
        super().__init__()

   
        # key: name; value: path to .json
        self.waveform_lst = {}     # list of registered waveforms
        self.envelope_lst = {}     # list of idata and qdata  
        self.program_lst = {}      # the program to be ran

        # register all .json files currently on disk into the above dicts
        self.waveform_lst = self._load_files_to_dict(self.waveform_dir_path)
        self.envelope_lst = self._load_files_to_dict(self.envelope_dir_path)
        self.program_lst = self._load_files_to_dict(self.program_dir_path)


        # start self.server on listening mode
        self.set_state("starting")   # does nothing other than indicating the status. SET_TO_LISTENING_STATUS() only from "starting"
                                      # or firing status
        
        # load the programming logic onto FPGA
        self.soc = QickSoc()
        self.soccfg = self.soc
        self.awg_prog = None         # AWGProgram to be created during compilation


        # start the server for listening, state will be set to listening
        # TODO: combine everything into start server, the server should set up when 
        # instantiated, then when calling start_server() then it should be ready to listen to 
        # connections and process commands 
        self.run_server()                # start the server and let it listen for client connections
                

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
        self.server_socket.bind((Server.host, Server.port))
        self.server_socket.listen()
        self.is_running = True
        print(f"Server listening on port {Server.port}...")

        # infinite loop to wait for connection 
        while True:
            try:
                conn, addr = self.server_socket.accept()
                print(f"Connected by {addr}")

                # loop to process commands 
                while True:
                    try: 
                        command = self.receive_string(conn)
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
                            print(f"Unknown command: {command}")

                    except Exception as e:
                        print(f"Error: {e}")
                        break

            except Exception as e:
                self.conn.close()
                print(f"Error: {e}")
            finally:
                self.conn.close()
                print(f"Connection to {addr} has been closed.")
                print(f"Server listening on port {Server.port}...")
        
        
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
    
    @status.setter
    def set_state(self, state):
        """
        set the AWG into server listening mode or firing mode 
        """        
        self.state = state
    
    
    def _check_matching_names(self, name, file_path):
        name_read = self._read_file_name(file_path)
        return name == name_read


    def upload_waveform_cfg(self, conn):
        if self.state != "listening":
            print(f"Can't receive file: current AWG state is {self.state}.")
            return 
        
        name = self.receive_string(conn)
        # if name here and the name in json have discrepancy, what should I do?

        # check if the given name and the name written in json are matched, if not, delete the written file and return
        filename = self.receive_file(conn, FPGA_AWG.waveform_dir_path)            # save the config file to disk; filename does not contain abs path
        file_path = os.path.join(FPGA_AWG.waveform_dir_path, filename).replace('\\', '/')
        if not self._check_matching_names(filename, file_path):
            print("Error: name in .json and the given name must match!")
            os.remove(file_path)
            return                   
        self.waveform_lst[name] = file_path

    

    def upload_envelope_data(self, conn):
        if self.state != "listening":
            print(f"Can't receive file: current AWG state is {self.state}.")
            return 
        # TODO: need to handle the None case, i.e. i data or q data is None

        i_name = self.receive_string(conn)
        i_filename = self.receive_file(conn, FPGA_AWG.envelope_dir_path)
        i_file_path = os.path.join(FPGA_AWG.envelope_dir_path, i_filename).replace('\\', '/')
        if not self._check_matching_names(i_filename, i_name):
            print("Error: name in .json and the given name must match!")
            os.remove(i_file_path)
            return 

        q_name = self.receive_string(conn)
        q_filename = self.receive_file(conn, FPGA_AWG.envelope_dir_path)
        q_file_path = os.path.join(FPGA_AWG.envelope_dir_path, q_filename).replace('\\', '/')
        if not self._check_matching_names(q_filename, q_name):
            print("Error: name in .json and the given name must match!")
            os.remove(q_file_path)
            return

        self.envelope_lst[i_name] = i_file_path
        self.envelope_lst[q_name] = q_file_path


    # upload the program config 
    def upload_program(self, conn):
        if self.state != "listening":
            print(f"Can't receive file: current AWG state is {self.state}.")
            return
        
        name = self.receive_string(conn)
        filename = self.receive_file(conn, FPGA_AWG.program_dir_path)
        file_path = os.path.join(FPGA_AWG.program_dir_path, filename).replace('\\', '/')
        if not self._check_matching_names(filename, file_path):
            print("Error: name in .json and the given name must match!")
            os.remove(file_path)
            return                   
        self.program_lst[name] = file_path


    def delete_waveform_config(self, conn):
        if self.state != "listening":
            print(f"Can't receive file: current AWG state is {self.state}.")
            return

        name = self.receive_string(conn)
        if name not in self.waveform_lst:
            print(f"Not found in waveform list: {name}")
        else:
            try:
                path = os.path.join(FPGA_AWG.waveform_dir_path, self.waveform_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.waveform_lst.pop(name)
            except Exception as e:
                print(f"Error: {e}")
                

    
    def delete_envelope_data(self, conn):
        if self.state != "listening":
            print(f"Can't delete file: current AWG state is {self.state}.")
            return 
        
        name = self.receive_string(conn)
        if name not in self.envelope_lst:
            print(f"Not found in envelope list: {name}")
        else:
            try:
                path = os.path.join(FPGA_AWG.envelope_dir_path, self.envelope_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.envelope_lst.pop(name)
            except Exception as e:
                print(f"Error: {e}")

    
    def delete_program(self, conn):
        if self.state != "listening":
            print(f"Can't delete file: current AWG state is {self.state}.")
            return
        
        name = self.receive_string(conn)
        if name not in self.program_lst:
            print(f"Not found in program list: {name}")
        else:
            try:
                path = os.path.join(FPGA_AWG.program_dir_path, self.program_lst[name]).replace('\\', '/')  # Ensure the path uses forward slashes
                os.remove(path)
                self.program_lst.pop(name)
            except Exception as e:
                print(f"Error: {e}")

    

    def set_trigger_mode(self, conn):
        if self.state != "listening":
            print(f"Can't set trigger: current AWG state is {self.state}.")
            return
        
        trig_mode = self.receive_string(conn)
        if trig_mode != "internal" and trig_mode != "external":
            print(f"{trig_mode} is not internal or external.") 
            return     
        self.trig_mode = trig_mode


            
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
    
    

        