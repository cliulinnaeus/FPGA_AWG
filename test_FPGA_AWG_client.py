from FPGA_AWG_client import *

client = FPGA_AWG_client()
client.connect(host="192.168.0.234", port=8080)

client.upload_waveform_cfg("test_wf_cfg.json", name="test_wf")

client.disconnect()
# if there are two files on the disk with different file name but the same name, then the old file should be overwritten 
# the easiest way to do it is just have a dict that points the name to the file name 
# to repoint, it needs to delete the old file, and upload the new file, then point the name to the file name of the new file
# client.upload_waveform_cfg("X_pulse.json", name="X")
# client.upload_waveform_cfg("Y_pulse.json", name="Y")
# client.upload_waveform_cfg("-Y_pulse.json", name="-Y")
# client.upload_waveform_cfg("-X_pulse.json", name="-X")

# # same logic applies here
# client.upload_program("XY8.json", name="XY8")
# client.upload_envelope_data(idata="X_i_envelope.json", qdata="X_q_envelope.json", iname="X_i_envelope", qname="X_q_envelope")

# client.set_trigger_mode(trig_mode="external")

# client.start_program("XY8")