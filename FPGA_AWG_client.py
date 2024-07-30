from client import *

# a python based client 
class FPGA_AWG_client(Client):

    def __init__(self):
        super().__init__()

    
    def upload_waveform_cfg(self, wf_cfg_path, name):
        if os.path.exists(wf_cfg_path):
            self.send_string("UPLOAD_WAVEFORM_CFG")
            self.send_string(name)
            self.send_file(wf_cfg_path)
            self.receive_server_ack()
        else:
            print(f"{wf_cfg_path} does not exist!")


    # Use this function to upload either i data or q data. 
    def upload_envelope_data(self, data_path, name):
        if os.path.exists(data_path):
            self.send_string("UPLOAD_ENVELOPE_DATA")
            self.send_string(name)
            # if file is sent successfully without client side error
            self.send_file(data_path)
            self.receive_server_ack()
        else: 
            print(f"{data_path} does not exist!")

    def upload_program(self, prog_cfg_path, name):
        if os.path.exists(prog_cfg_path):
            self.send_string("UPLOAD_PROGRAM")
            self.send_string(name)
            self.send_file(prog_cfg_path)
            self.receive_server_ack()
        else: 
            print(f"{prog_cfg_path} does not exist!")


    def delete_waveform_cfg(self, name):
        self.send_string("DELETE_WAVEFORM_CFG")
        self.send_string(name)
        self.receive_server_ack()


    def delete_envelope_data(self, name):
        self.send_string("DELETE_ENVELOPE_DATA")
        self.send_string(name)
        self.receive_server_ack()



    def delete_program(self, name):
        self.send_string("DELETE_PROGRAM")
        self.send_string(name)
        self.receive_server_ack()

    def get_waveform_lst(self):
        self.send_string("GET_WAVEFORM_LIST")
        self.receive_server_ack()

    def get_envelope_lst(self):
        self.send_string("GET_ENVELOPE_LIST")
        self.receive_server_ack()

    def get_program_lst(self):
        self.send_string("GET_PROGRAM_LIST")
        self.receive_server_ack()

    def get_state(self):
        self.send_string("GET_STATE")
        self.receive_server_ack()

    def start_program(self, name):
        self.send_string("START_PROGRAM")
        self.send_string(name)

    def stop_program(self):
        self.send_string("STOP_PROGRAM")

    def check_state(self):
        self.send_string("CHECK_STATE")

    def set_trigger_mode(self, trig_mode):
        self.send_string("SET_TRIGGER_MODE")
        self.send_string(trig_mode)
        
        






