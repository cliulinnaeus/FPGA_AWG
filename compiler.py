from qick import *
from FPGA_AWG import waveform_dir_path, envelope_dir_path, program_dir_path
import json
from queue import PriorityQueue

class Compiler():

    """
    Page 
        $0: 0 
        $1: freq
        $2: 
        ...
        $5: mode code
        $6: time for this pulse
        ...
        $31: not used

    Rules to play pulses:
    1. all 6 pulse registers must be on the same page
    2. each channel has its own envelope memory

    special cases:
    1. pulse "X" is played on multiple channels at different times with potentially overlaps
        You can schedule the earliest X pulse to be played, then change time register, play again on a diff 
        ch. Once a SET instruction is ran, you can change the reg values even the pulse is not finished playing
    2. 

    """



    # the ZERO reg of each page indicate number 0 and should not be used
    # table to indicate which register on which page is used
    NUM_REG = 32    # number of registers per page
    NUM_PAGE = 8    # page 0 is reserved for loop counter
    REG_PTR_STEP = 6    # reg pointer increment step size, i.e. number of registers for each pulse
                        # there are 6 regs per pulse, here the time reg is excluded 
                        # instead, the last reg of each page is used as the time reg for that channel
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
        # pulse length look up table. key: pulse name, value: pulse length in # clk cycles
        self.pulse_length_LUT = {}
        # pulse style look up table (const, arb, buffer). key: pulse name, value: style
        # this is used by the scheduler to determine whether the pulse needs to use special addr register
        self.pulse_style_LUT = {}



    def tokenize(self, prog_line):
        """
        parse the prog_line into a list of string "X", "Y" (pulse names)
        e.g.
        INPUT: "[loop(2,[X, loop(3,[10, Y]),Y,Z]), X]"
        OUTPUT: ['loop', '2', '[X,loop(3,[10,Y]),Y,Z]', 'X']

        INPUT: "[loop(10, [X, Y, X, Y, Y, X, Y, X]), X]"
        OUTPUT: ['loop', '10', '[X,Y,X,Y,Y,X,Y,X]', 'X']

        INPUT: "[X, Y, X, Y, Y, X, Y, X]"
        OUTPUT: ['X', 'Y', 'X', 'Y', 'Y', 'X', 'Y', 'X']
        """
        # add special character "\n" to indicate end of the line
        EOL_char = '\n'
        prog_line = prog_line.strip("[]").replace(" ", "") + EOL_char
        prog_line = iter(prog_line)
        in_loop = False
        curr_token = ""
        open_parenthesis = 0
        result = []
        for c in prog_line:
            if not in_loop:
                if c == ",":
                    if curr_token != "":
                        result.append(curr_token)
                        curr_token = ""   
                    # the case where it just come out of the loop
                    else:
                        pass
                elif curr_token == "loop":
                    # c must be "("
                    result.append("loop")
                    curr_token = ""
                    in_loop = True
                    open_parenthesis += 1
                else:
                    # detect end of prog_line
                    if c == EOL_char:
                        if curr_token != "":
                            result.append(curr_token)
                    # otherwise just accumulate curr_token
                    else:
                        curr_token += c                    
            else:
                # read loop count until the first "," in loop
                while c != ",":
                    curr_token += c
                    c = next(prog_line)
                result.append(curr_token)    # save loop count
                curr_token = ""
                # read until there are no open parenthesis, then we are out of the loop
                for c in prog_line:
                    if c == "(":
                        open_parenthesis += 1
                    elif c == ")":
                        open_parenthesis -= 1
                        
                    if open_parenthesis > 0:
                        curr_token += c
                    else:
                        result.append(curr_token)
                        curr_token = ""
                        in_loop = False
                        break
        return result


    def _is_loop_body(self, token):
        # checks if token is loop body, i.e. []
        return token.startswith('[') and token.endswith(']')


    def list_all_pulses(self, tokens_set, tokens):
        """
        TOKENS_SET: an empty set to store all pulse names
        TOKENS_LST: the output of tokenize (for one channel)

        Modifies tokens_set by adding pulse name from tokens_lst into tokens_set
        """
        for t in tokens:
            # loop body is not tokenize, so it needs to be further tokenized
            if self._is_loop_body(t):
                self.list_all_pulses(tokens_set, self.tokenize(t))
            else:
                # if t is a number, this means to wait, so don't save it in the set
                if not t.isnumeric() and t != "loop":
                    tokens_set.add(t)



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
        tokenize pulses, create prog IR (intermediate representation), load pulse param 
        into registers, schedule pulse play time
        """
        prog_cfg = self.load_program_cfg(prog_name)
        prog_structure = prog_cfg["prog_structure"]
        # create a set of pulse names across all channels for allocating pulse param registers
        token_set = set()
        tokens_dict = {}
        for ch, prog_line in prog_structure.items():
            tokens = self.tokenize(prog_line)    # tokenize each prog line 
            # list_all_pulses also recursively tokenize loop bodies
            self.list_all_pulses(token_set, tokens)    # list all appeared pulse names in token_set
            tokens_dict[ch] = tokens    # saves tokens at each ch for scheduler
        
        # generate asm code for allocate registers for each pulse that appeared across all channels
        for pulse_name in token_set:
            pulse_cfg = self.load_pulses_cfg(pulse_name)
            # save the pulse length to LUT
            self.pulse_length_LUT[pulse_name] = pulse_cfg["length"]
            self.pulse_style_LUT[pulse_name] = pulse_cfg["style"]
            # generate asm code
            self.alloc_registers(pulse_cfg)
        
        # run the scheduler to generate asm code for running pulses according to prog structure
        scheduler = Scheduler(self, tokens_dict)
        scheduler_generator = scheduler.schedule_next()
        for fire_pulse_params in scheduler_generator:
            [ch, start_time, pulse_name] = fire_pulse_params
            self.fire_pulse(ch, start_time, pulse_name)
        p.end()



    def fire_pulse(self, ch, start_time, pulse_name):
        """
        Generate asm code for firing pulse at ch at start_time
        """


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
        # time register should be $6, $12, $18, $24, $30
        self.reg_LUT[pulse_name] = self._curr_reg_ptr
        # increment the register and page pointer
        self._step_reg_ptr()

    

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


class Scheduler():
    """
    contains a list of channels
    each channel has a time property 
    needs to compile pulses across multiple channels into a single line
    channel.time is the time at which the next pulse is played immediately

    need to sort all events based on their start time across diff channels
    """


    def __init__(self, compiler, tokens_dict):

        self.compiler = compiler
        # key: ch, value: tokens 
        self.tokens_dict = tokens_dict
        # dict to keep track of current pulse start time at each channel
        # key: ch, value: start time of next pulse 
        self.curr_times = {}
        # init curr_time dict. use in ir instead of ir.keys() because it's faster
        for ch in self.tokens_dict:
            self.curr_times[ch] = 0
        # dict that stores one generator for each channel
        self.gen_dict = {}
        # create next pulse generator for each channel
        for ch, tokens in self.tokens_dict.items():
            self.gen_dict[ch] = self.next_pulse(tokens)

    
    def schedule_next(self):
        """
        when called, gives the name of the next pulse,
        time it is played, and the channel it is played on
        this should update all channel timers 
        returns the one with the smallest timer value

        there should be a function that converts each line to the 
        next pulse it outputs 

        IR: intermediate representation, is a dict of token list corresponding to each diff channels
            key: ch, value: token list
        
        loop:
        calls next_pulse on each channel and save them to priority queue
        advance timer on each channel
        dequeue once and make asm
        enqueue the next one

        yields (next_pulse_name, ch, start_time)
        
        """

        # played at the same time
        q = PriorityQueue()

        # first, save first pulse from all channels into the queue, advance each timer accordingly
        for ch, next_pulse_gen in self.gen_dict.items():
            # enqueue the first token that's not a wait time, which is a pulse name
            for token in next_pulse_gen:                
                if token.isnumeric():    # if it's a number, it's a wait time
                    self.curr_times[ch] += int(token)
                else:    # if it's a pulse name
                    q.put((self.curr_times[ch], (ch, token)))
                    break
        
        while True:
            # get the earliest pulse (q.get() returns (prio, item))
            (ch, pulse_name) = q.get()[1]
            # yield channel, start time, pulse name
            yield [ch, self.curr_times[ch], pulse_name]
            # update new pulse start time
            self.curr_times[ch] += self.compiler.pulse_length_LUT[pulse_name]
            if q.empty():
                break

            # on the current channel enqueue the first token that's not a wait time, which is a pulse name
            for token in self.gen_dict[ch]:                
                if token.isnumeric():    # if it's a number, it's a wait time
                    self.curr_times[ch] += int(token)
                else:    # if it's a pulse name
                    q.put((self.curr_times[ch], (ch, token)))
                    break

    def next_token(self, line_token_lst): 
        """
        Helper function to convert a token list to a generator
        """
        for token in line_token_lst:
            yield token

    def next_pulse(self, tokens):
        """
        Gives the next pulse for just one channel. Unwraps nested loops
        uses yield instead of return so that the for loop can be continued
        yields the string name of the pulse to be played or the wait time
        """
        tokens = iter(tokens)

        for t in tokens:
            if t == "loop":
                # make generator step next to get loop_count
                loop_count = int(next(tokens))
                # loop body should be a string rep of list
                loop_body_tokens = self.compiler.tokenize(next(next_token_gen))
                # use yield instead of return so that for loop can be continued
                for _ in range(loop_count):
                    yield from self.next_pulse(loop_body_tokens)
            else:
                # handle pulse 
                yield token

        