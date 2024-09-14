from qick import *
from FPGA_AWG import waveform_dir_path, envelope_dir_path, program_dir_path
import json


class Compiler():

    # the ZERO reg of each page indicate number 0 and should not be used
    # table to indicate which register on which page is used
    NUM_REG = 32    # number of registers per page
    NUM_PAGE = 8    # page 0 is reserved for loop counter
    REG_PTR_STEP = 6    # reg pointer increment step size, i.e. number of registers for each pulse
    PAGE_PTR_STEP = 1
    NUM_CHANNELS = 7



    def __init__(self, awg_prog):
        self.awg_prog = awg_prog
        self._curr_reg_ptr = 1
        self._curr_page_ptr = 1
        # assumes all channels of QickProgram are the same generator, pick 0th gen, get samps_per_clk
        # samps_per_clk is default 16
        self.samps_per_clk = self.awg_prog.soccfg['gens'][0]['samps_per_clk']
        self.maxv = self.awg_prog.soccfg['gens'][0]['maxv']
        # register look up table. key: pulse_name, value: pointer for the first register (freq)
        self.reg_LUT = {}

    def parse_prog_line(self, prog_line):
        """
        parse the prog_line into a list of string "X", "Y" (pulse names)
        remove duplicate 
        """
        token_lst = prog_line.strip("[]").replace(" ", "").split(",")
        # converts all the number strings to int
        token_lst = [int(item) if item.isdigit() else item for item in token_lst]
        # token_set = set(token_lst)    # remove duplicate items by converting to set
        return token_lst

    def _step_reg_ptr(self):
        """
        if next 6 registers exceeds the number of registers per page, 
        increment page pointer
        """
        if self._curr_reg_ptr + Compiler.REG_PTR_STEP > Compiler.NUM_REG:
            self._curr_reg_ptr = 1
            self._step_page_ptr()
        else:
            self._curr_reg_ptr  = self._curr_reg_ptr + Compiler.REG_PTR_STEP

    def _step_page_ptr(self):
        """
        increment the page pointer, if overflow, raise error
        """
        if self._curr_page_ptr + Compiler.PAGE_PTR_STEP > Compiler.NUM_PAGE:
            raise RuntimeError(f"Compilation Error: No available registers left (page: {self._curr_page_ptr}, reg: {self._curr_reg_ptr})")
        self._curr_page_ptr = self._curr_page_ptr + Compiler.PAGE_PTR_STEP


    def compile(self, prog_name):
        """
        Compilation consists of the following steps:
        tokemize pulses, create prog IR (intermediate representation), load pulse param 
        into registers, schedule pulse play time
        """
        prog_cfg = self.load_program_cfg(prog_name)
        prog_structure = prog_cfg["prog_structure"]
        # set of pulse names and wait time 
        token_set = set()
        for ch, prog_line in prog_structure.items():
            line_token_lst = self.parse_prog_line(prog_line)
            token_set.update(line_token_lst)    # add to tokens to set to remove duplicate
        # TODO: need to handle nested loops and wait time separately
        # load pulses into registers first; this generates a bunch of REGWI asm instructions
        for pulse_name in token_set:
            self.alloc_registers(pulse_name)
        
        # run the scheduler to generate asm code for running pulses according to prog structure
        self.schedule_pulse_time()


        return




    def alloc_registers(self, pulse_cfg):
        """
        alloc registers at curr_reg_ptr and curr_page_ptr for a specific pulse
        It allocates freq, phase, gain, phrst, mode, outsel, stdysel, and load memory data to
        addr of every ch (all channels 0-7), it does not populate the t register 
        """
        p = self.awg_prog
        pulse_name = pulse_cfg["pulse_name"]
        style = pulse_cfg["style"]
        freq = p.freq2reg(f=pulse_cfg["freq"])
        phase = p.deg2reg(deg=pulse_cfg["phase"])
        gain = pulse_cfg["gain"]
        phrst = pulse_cfg.get("phrst")    # is None if not defined
        mode = pulse_cfg.get("mode")
        outsel = pulse_cfg.get("outsel")
        stdysel = pulse_cfg.get("stdysel")
        length = pulse_cfg["length"]
        i_data_name = pulse_cfg.get("i_data_name")
        q_data_name = pulse_cfg.get("q_data_name")

        i_data = self.load_envelope_cfg(i_data_name)
        q_data = self.load_envelope_cfg(q_data_name)

        env_length = len(i_data) // self.samps_per_clk

        # load all params to registers
        # safe_regwi make sure successful write if a number is more than 30 bits (see qick.asm_v1)
        p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr, freq, comment=f"freq = {freq}")
        p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 1, phase, comment=f"phase = {phase}")
        p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 2, gain, comment=f"gain = {gain}")

        # set 
        if style == 'const':
            # use addr 0 if style is const
            addr_reg = 0
            # make the mode code
            mc = p.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel="dds", length=length)
            p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 4, mc, comment=f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
        elif style == 'arb':

            # this block of codes below performs a shitty trick - saves the memory on addr of 
            # each ch 

            # add evelope to all channels that uses this pulse
            # for a single pulse on different ch, every ch has a different addr
            for ch in range(Compiler.NUM_CHANNELS):
                # add_envelope will round data elements to integers
                # this line calculates the memory addr for each ch
                p.add_envelope(ch=ch, name=pulse_name, idata=i_data, qdata=q_data)
                # each channel has a diff memory block, if I want to play same pulse on diff ch,
                # I need to save diff addr on each
            addr = p.envelopes[0]['envs'][pulse_name]["addr"]
            # write the correct addr to register
            p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 3, addr, comment=f"pulse {pulse_name} mem addr = {addr}")
            
            # make the mode code
            mc = p.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel=outsel, length=env_length)
            p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 4, mc, comment=f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
            
        elif style == 'buffer':
           pass

        """I decide to not include flat_top as it requires 4 registers to define (addr_ramp_down, three reg for phrst|stdysel|mode|outsel)
        each page can only have 31 registers ($0 reserved for the literal 0), each pulse needs 6 reg, so each page has a spare reg $31
        But the SET instruction can only take registers on the same page, so correctly allocating the registers for flat_top is 
        not straightforward. On the other hand, one can just define three pulses and put them together to form the flat_top pulse.
        """
        # save the first register pointer to LUT
        # time register should be
        # $6, $12, $18, $24, $30
        self.reg_LUT[pulse_name] = self._curr_reg_ptr
        # increment the register and page pointer
        self._step_reg_ptr()



    def schedule_pulse_time():
        """
        Compute the pulse time to play each pulse on each channel
        """
        # iterate through the IR, for each pulse, run SET command 
        

        return
    

    def load_program_cfg(self, prog_name):
        """
        Load program.json to a dict
        """
        directory_path = FPGA_AWG.program_dir_path
        file_path = os.path.join(directory_path, prog_name + '.json').replace('\\', '/')
        with open(file_path, 'rb' as file):
            prog_cfg = json.load(file)
        return prog_cfg    # a list of numbers


    def load_envelope_data(self, env_name):
        """
        Load env data from disk to a list
        """
        directory_path = FPGA_AWG.envelope_dir_path
        file_path = os.path.join(directory_path, env_name + '.json').replace('\\', '/')
        with open(file_path, 'rb' as file):
            envelope = json.load(file)
        return envelope    # a list of numbers


    def load_pulses_cfg(self, pulse_name):
        """
        read pulse.json and load it into a dictionary
        """
        directory_path = FPGA_AWG.waveform_dir_path
        file_path = os.path.join(directory_path, pulse_name + '.json').replace('\\', '/')
        with open(file_path, 'rb' as file):
            pulse_cfg = json.load(file)
        return pulse_cfg


        