from client import *

# a python based client 
class FPGA_AWG_client(Client):

    def __init__(self):
        super().__init__()

    
    def upload_waveform_cfg(self, wf_cfg_path, name):
        self.send_string("UPLOAD_WAVEFORM_CFG")
        self.send_string(name)
        self.send_file(wf_cfg_path)
        self.receive_server_ack()

    # Use this function to upload either i data or q data. 
    def upload_envelope_data(self, data_path, name):
        self.send_string("UPLOAD_ENVELOPE_DATA")
        self.send_string(name)
        self.send_file(data_path)
        self.receive_server_ack()


    def upload_program(self, prog_cfg_path, name):
        self.send_string("UPLOAD_PROGRAM")
        self.send_string(name)
        self.send_file(prog_cfg_path)
        self.receive_server_ack()


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
        
        






