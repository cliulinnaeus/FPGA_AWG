from client import *



# a python based client 
class FPGA_AWG_client(Client):

    def __init__(self, host, port):
        super().__init__(host, port)

    
    def upload_waveform_cfg(self, wf_cfg_path, name):
        self.send_string("UPLOAD_WAVEFORM_CFG")
        self.send_string(name)
        self.send_file(wf_cfg_path)


    def upload_envelope_data(self, idata_path, qdata_path, i_name, q_name):
        self.send_string("UPLOAD_ENVELOPE_DATA")
        self.send_string(i_name)
        self.send_file(idata_path)
        self.send_string(q_name)
        self.send_file(qdata_path)

    def upload_program(self, prog_cfg_path, name):
        self.send_string("UPLOAD_PROGRAM")
        self.send_string(name)
        self.send_file(prog_cfg_path)

    def delete_waveform_cfg(self, name):
        self.send_string("DELETE_WAVEFORM_CFG")
        self.send_string(name)

    def delete_envelope_data(self, name):
        self.send_string("DELETE_ENVELOPE_DATA")
        self.send_string(name)

    def delete_program(self, name):
        self.send_string("DELETE_PROGRAM")
        self.send_string(name)

    def start_program(self, name):
        self.send_string("START_PROGRAM")
        self.send_string(name)

    def stop_program(self):
        self.send_string("STOP_PROGRAM")

    def check_state(self):
        self.send_string("CHECK_STATE")
        
        






