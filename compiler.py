from qick import *
from FPGA_AWG import waveform_dir_path, envelope_dir_path, program_dir_path
import json


class Compiler():

    # the ZERO reg of each page indicate number 0 and should not be used
    # table to indicate which register on which page is used
    reg_lookup_table = []
    NUM_REG = 32    # number of registers per page
    NUM_PAGE = 8    # page 0 is reserved for loop counter
    REG_PTR_STEP = 6    # reg pointer increment step size, i.e. number of registers for each pulse - 1 
    PAGE_PTR_STEP = 1


    def __init__(self, awg_prog):
        self.awg_prog = awg_prog
        self._curr_reg_ptr = 1
        self._curr_page_ptr = 1
        # assumes all channels of QickProgram are the same generator, pick 0th gen, get samps_per_clk
        # samps_per_clk is default 16
        self.samps_per_clk = self.awg_prog.soccfg['gens'][0]['samps_per_clk']
        self.maxv = self.awg_prog.soccfg['gens'][0]['maxv']

    def parse_prog_line(self, prog_line):
        """
        parse the prog_line into a list of string "X", "Y" (pulse names)
        remove duplicate 
        """
        token_lst = prog_line.strip("[]").replace(" ", "").split(",")
        # converts all the number strings to int
        token_lst = [int(item) if item.isdigit() else item for item in token_lst]
        token_set = set(token_lst)    # remove duplicate items by converting to set
        return token_set

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


    def alloc_registers(self, pulse_cfg):
        # alloc registers at curr_reg_ptr and curr_page_ptr
        p = self.awg_prog
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

        # load the waveform addr 
        if style == "const":
            addr_reg = 0
        else:
            # need to write a number to addr 
            addr_reg = self._curr_reg_ptr + 3

        # set 
        if style == 'const':
            mc = p.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel="dds", length=length)
            p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 4, mc, comment=f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
        elif style == 'arb':
            mc = p.get_mode_code(phrst=phrst, stdysel=stdysel, mode=mode, outsel=outsel, length=env_length)
            p.safe_regwi(self._curr_page_ptr, self._curr_reg_ptr + 4, mc, comment=f'phrst| stdysel | mode | | outsel = 0b{mc//2**16:>05b} | length = {mc % 2**16} ')
        elif style == 'buffer':
            pass

        """I decide to not include flat_top as it requires 4 registers to define (addr_ramp_down, three reg for phrst|stdysel|mode|outsel)
        each page can only have 31 registers ($0 reserved for the literal 0), each pulse needs 6 reg, so each page has a spare reg $31
        But the SET instruction can only take registers on the same page, so correctly allocating the registers for flat_top is 
        not straightforward. On the other hand, one can just define three pulses and put them together to form the flat_top pulse.
         """
        # increment the register and page pointer
        self._step_reg_ptr()



    def write_envelope_to_mem(self, i_data, q_data):
        """
        Checks if i_data, q_data are the same length, not exceeding maximum value,
        or len is int multiple of samps_per_clk
        Copied from Qick add_envelope()
        """

        length = [len(d) for d in [i_data, q_data] if d is not None]
        if len(length) == 0:
            raise RuntimeError("Error: no data argument was supplied")
        # if both arrays were defined, they must be the same length
        if len(length) > 1 and length[0] != length[1]:
            raise RuntimeError("Error: I and Q envelope lengths must be equal")
        length = length[0]

        if (length % self.samps_per_clk) != 0:
            raise RuntimeError("Error: envelope lengths must be an integer multiple of %d"%(self.samps_per_clk))

        # currently, all gens with envelopes use int16 for I and Q
        data = np.zeros((length, 2), dtype=np.int16)

        for i, d in enumerate([i_data, q_data]):
            if d is not None:
                # range check
                if np.max(np.abs(d)) > self.maxv:
                    raise ValueError("max abs val of envelope (%d) exceeds limit (%d)" % (np.max(np.abs(d)), self.maxv))
                # copy data
                data[:,i] = np.round(d)

        # write the data to memory



        return addr, length

    

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


        return addr, length

    def load_pulses_cfg(self, pulse_name):
        """
        read pulse.json and load it into a dictionary
        """
        directory_path = FPGA_AWG.waveform_dir_path
        file_path = os.path.join(directory_path, pulse_name + '.json').replace('\\', '/')
        with open(file_path, 'rb' as file):
            pulse_cfg = json.load(file)
        return pulse_cfg


        