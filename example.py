

###### server side code #########################
AWG = FPGA_AWG()    # server is now listening   #
AWG.run_server()                                #
#################################################




###### client side code #########################
#                                               #
#                                               #
#################################################
from FPGA_AWG_client import *

# create json file for wf and envelope
wf_config = {freq: 10, amp: 11, mode:"arb"}    # don't include time
idata = [...]
qdata = [...]

# needs a compiler for asm code 
prog_cfg = {ch1:
rep([X, I, X_gauss, Y, rep([Y, I], 20), I, I], 10),
[X, Y, Z, I],

ch2: [...]
}
# if X_gauss and X have the same reg parameter, then they should use the same
# just add gauss envelope to X_gauss


client = FPGA_AWG_client()
client.connect(host="192.168.0.234", port=8080)
# if there are two files on the disk with different file name but the same name, then the old file should be overwritten 
# the easiest way to do it is just have a dict that points the name to the file name 
# to repoint, it needs to delete the old file, and upload the new file, then point the name to the file name of the new file
client.upload_waveform_cfg("X_pulse.json", name="X")
client.upload_waveform_cfg("Y_pulse.json", name="Y")
client.upload_waveform_cfg("-Y_pulse.json", name="-Y")
client.upload_waveform_cfg("-X_pulse.json", name="-X")

# same logic applies here
client.upload_program("XY8.json", name="XY8")
client.upload_envelope_data(idata="X_i_envelope.json", qdata="X_q_envelope.json", iname="X_i_envelope", qname="X_q_envelope")

client.set_trigger_mode(trig_mode="external")

client.start_program("XY8")



