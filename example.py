AWG = FPGA_AWG()    # server is now listening

wf_config = {freq: 10, amp: 11, mode:"arb", env_name...}    # don't include time
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



AWG.upload_waveform_config(wf_config, name=X)
AWG.upload_envelope_data(idata, qdata, name)
AWG.upload_program_config(prog_cfg, name)
print(AWG.get_waveform_lst)
... 
AWG.set_trigger_mode("external")
AWG.start_program(prog_name)    # run the current program, AWG switches to firing mode
AWG.stop_program()    # stops whichever program is running, goes back to listening mode


