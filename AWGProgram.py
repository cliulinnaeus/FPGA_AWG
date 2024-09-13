from qick import *

class AWGProgram(QickProgram):

    SAMPLE_FREQ = 3000     # sampling rate to determine output nyquist zone

    def __init__(self, soccfg, cfg):
        super().__init__(soccfg)
        self.cfg = cfg
        
        self.make_program()  
        # this is a 1-D loop
        loop_dims = [self.cfg['reps']]    # how many times the code in self.body() gets ran
        self.iq_file_path = self.cfg["iq_file_path"]

        
    def add_config(self):
        return 
    
    
    def read_iq_data(self, file_path):
        
        
        return idata, qdata
    
    


    def compile_awg_program(self, prog_path):
        # need t


        return 



    def initialize(self):
        """
        To run once before body
        """
        res_ch = self.cfg["res_ch"]    # generator channel (index in 'gens' list)
        style = self.cfg["pulse_style"]    # choose between 'const', 'arb', and 'flat_top'
        freq = self.freq2reg(f=self.cfg["freq"], gen_ch=res_ch)    # converts freq in MHz into register value
        phase = self.deg2reg(deg=self.cfg["phase"], gen_ch=res_ch)  # Phase (register value)
        gain = self.cfg["gain"]    # Gain (DAC units), from -32768 to 32767
#         phrst = 0     # if 1, it resets the phase coherent accumulator
#         stdysel = 1   # selects what to output after the pulse is finished; 0: last calculated sample; 1: zero
        mode = self.cfg["mode"]      # what to do after queue is empty; oneshot: stop; periodic: repeat curr waveform
#         outsel = 
        length = self.cfg["length"]        
        idata, qdata = self.read_iq_data(self.iq_file_path)



        ################################
        
        # if frequency is above sampling freq, output more power in the second NQZ
        nqz = 1
        if freq > AWGProgram.SAMPLE_FREQ:
            nqz = 2
        self.declare_gen(ch=self.cfg["res_ch"], nqz=nqz) 

        self.default_pulse_registers(ch=res_ch, freq=freq, phase=phase, gain=gain)
        
        # add envelop waveform data
        if style in ["flat_top", "arb"]:
            #The I and Q arrays must be of equal length, and the length must be divisible by the samples-per-clock of this generator
            # TODO: obtain idata and qdata
            self.add_envelope(ch=res_ch, name="envelope", idata=idata, qdata=qdata)
            
        if style == "const":
            self.set_pulse_registers(ch=res_ch, style=style, length=length, mode=mode)    # overrides outsel and uses DDS mode
        elif style == "flat_top":
            # The first half of the waveform ramps up the pulse, the second half ramps down the pulse
            self.set_pulse_registers(ch=res_ch, style=style, waveform="envelope", length=length, mode=mode)
        elif style == "arb":
            self.set_pulse_registers(ch=res_ch, style=style, waveform="envelope", mode=mode)
        
        
#         ch : int
#             generator channel (index in 'gens' list)
#         style : str
#             Pulse style ("const", "arb", "flat_top")
#         freq : int
#             Frequency (register value)
#         phase : int
#             Phase (register value)
#         gain : int
#             Gain (DAC units)
#         phrst : int
#             If 1, it resets the phase coherent accumulator
#         stdysel : str
#             Selects what value is output continuously by the signal generator after the generation of a pulse. If "last", it is the last calculated sample of the pulse. If "zero", it is a zero value.
#         mode : str
#             Selects whether the output is "oneshot" or "periodic"
#         outsel : str
#             Selects the output source. The output is complex. Tables define envelopes for I and Q. If "product", the output is the product of table and DDS. If "dds", the output is the DDS only. If "input", the output is from the table for the real part, and zeros for the imaginary part. If "zero", the output is always zero.
#         length : int
#             The number of fabric clock cycles in the flat portion of the pulse, used for "const" and "flat_top" styles
#         waveform : str
#             Name of the envelope waveform loaded with add_envelope(), used for "arb" and "flat_top" styles
#         mask : list of int
#             for a muxed signal generator, the list of tones to enable for this pulse
        
        self.synci(200)    # give the processor some time to configure pulses. i.e. let the generator pause for 200 clk cycles and
        # set zero time of the generator to 200 clk cycles 
        
    
    def body(self): 
        """
        To run repeatedly for self.cfg['reps'] times
        """
        ch = self.cfg["res_ch"]
        t = self.cfg["t"]
        self.sync_all(t=t)
        self.pulse(ch=ch, t=0)
        
    
    def make_one_pulse(self, pulse_cfg):
        """
        make the program that fires one pulse for REPS number of times
        """
        ch = pulse_cfg["res_ch"]
        t = pulse_cfg["t"]
        reps = pulse_cfg['reps']
        
        # treat case RESP == 1 specifically to save time writing to registers and looping
        if reps == 1: 
            self.sync_all(t=t)
            self.pulse(ch=ch, t=0)
        else:        
            rjj = 14
            self.regwi(0, rjj, reps-1)
            self.label("LOOP_J")

            self.sync_all(t=t)
            self.pulse(ch=ch, t=0)

            self.loopnz(0, rjj, "LOOP_J")
        # don't call self.end() here as there may be more pulses 
    
    
    def make_program(self):
        """
        A template program which repeats the instructions defined in the body() method the number of times specified in self.cfg["reps"].
        """
        p = self

        rjj = 14     # default to use page 0 register $14 for counter
        p.initialize()
        p.regwi(0, rjj, self.cfg['reps']-1)
        p.label("LOOP_J")

        p.body()

        p.loopnz(0, rjj, 'LOOP_J')

        p.end()
    
    