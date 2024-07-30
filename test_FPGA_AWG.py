from FPGA_AWG import *




if __name__ == '__main__':
    awg = FPGA_AWG()
    print("created AWG")
    awg.run_server()