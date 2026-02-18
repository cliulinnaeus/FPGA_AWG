# QICK-AWG: Flexible Arbitrary Waveform Generation for Experimental Setups
### (More documentations will be added)
QICK-AWG is a specialized software package that transforms a QICK-based FPGA into an Arbitrary Waveform Generator (AWG) designed to integrate seamlessly into diverse experimental setups. Many labs already equipped with experiment control hardware and software face challenges integrating QICK without substantial modifications, as QICK is a self-contained and specialized library. QICK-AWG bridges this gap by enabling QICK-based FPGA boards to function solely as AWGs, concentrating on generating customizable pulse sequences for flexible waveform generation. This program is suitable for doing complex dynamical decoupling sequences in atomic, molecular, optical (AMO) experiments such as the NV-centers. 

Built on top of the QICK library, this codebase provides a straightforward programming interface. When deployed, the FPGA operates as an AWG, actively listening for and responding to user commands through a network socket. Note that this initial version does not yet support in situ pulse parameter sweep, which is a planned update in future versions.

Note: 
- This software supports both ZCU111 and RFSoC4x2. 
- This software does not yet support in situ pulse parameter sweeps, which can be used to realize adiabatic passage sequences. This is a planned update in future versions.
- Please report any bugs to me. 

See the original QICK repository at: https://github.com/openquantumhardware/qick

## Installation

### Prerequisites
It is assumed you start with a brand new ZCU111 board. If you have an old board with already installed newest version of QICK, you may want to consider downgrading it. 

You can find an working (and older) version of QICK [here](https://github.com/yao-lab-harvard/qick). Clone this repository onto your FPGA. 

You need a client computer to be connect to the same LAN as the FPGA. 

### Installation instructions
This package needs to be downloaded on both the QICK board and the client computer. 

#### Installation on the QICK board
Follow the quick start guide in QICK repository but do not run the installation jupyter notebook _000_Install_qick_package.ipynb_ in _qick_demos_: [QICK qick start guide](https://github.com/openquantumhardware/qick/tree/main/quick_start)
Run the following in shell
ssh into the FPGA address, e.g.
```
ssh xilinx@192.168.0.123
```
it will ask for the password, the password is _xilinx_ 

check current directory
```
ls jupyter_notebooks
```
and you should see a repository _qick_ being listed.
```
cd jupyter_notebooks/qick
```
Get root access (the QICK library can only be ran under root access, which means it has to be installed under root)
```
su
```
enter password _xilinx_ again. A new line should initiate with _root@pynq:_

run the installation program
```
pip3 install -e .
```
At this point the QICK library should already be installed. Check if you have correctly installed QICK by opening an interactive python session:
```
python3 -i
```
```
import qick
print(qick.__version__)
```
A correct installation will tell you the version, e.g. _'0.2.191'_

Now let's install the QICK_AWG repo.
First exit out of the interactive python session and run the following in your shell
```
cd /home/xilinx
git clone https://github.com/cliulinnaeus/FPGA_AWG.git
cd FPGA_AWG
```
You are now ready to go! 

#### Installation on the client computer
Simply git clone this repo to a good location. 




## Tutorial

### General Description
To run the AWG program, run the following in the _FPGA_AWG_ directory
```
python3 run_server.py
```
This initializes a server object on the FPGA and it actively listens to commands send to it.



### How to define a waveform

To program a pulse sequence, the first thing to do is to define all the necessary waveforms used in the pulse sequence. In a spin echo sequence, two distinct waveforms are used, an X-pi/2 pulse and an X-pi pulse. Therefore you need to define them. The waveform configuration files are defined in the .json format. Here is an example

```
{
    "pulse_name": "X_enveloped",
    "style": "arb",
    "freq": 2000,
    "gain": 30000,
    "phase": 0,
    "length": 10,
    "mode": "oneshot",
    "i_data_name": "half_circle",
    "q_data_name": "half_circle"
}
```

pulse_name: the name of the pulse that will be used to call the pulse in the program configuration file

style: switch between "const" and "arb". For "const", the server directly generates sine waves using DDS output, the time resolution is limited to 2.6ns, which is one clock cycle. The shortest pulse length is limited to 3 clock cycles. There is no memory limitation in this style, any pulse sequence can be ran indefinitely. For "arb", the server multiples the DDS output with the memory (envelope data) and outputs the product. 

freq: in units of MHz, can go from 0 to 6000. Importantly, the sampling frequency of the server is around 3000MHz, so above 3000MHz there will be aliasing due to Nyquist theory.

gain: goes from -2^15 to 2^15-1. For negative numbers the absolute value is the same, but the phase is off by 180 deg. 

phase: in units of degree

length: in units of clock cycle (2.6ns), minimum is 3

mode: "oneshot" or "periodic". In oneshot mode, the pulse sequence program will only be run once, in periodic mode, the last pulse in the pulse sequence will be ran indefinitely after the whole sequence is ran once. 

i_data_name: the name of the .csv file for the envelope data

q_data_name: the name of the .csv file for the envelope data

""





### How to write a program

Program configuration files must written in the .json format. Each configuration file must include two necessary keys: "name" and "prog_structure". The name must match with the name you use in the client.upload_program_config() function. In the prog_structure field you can define the pulse sequence using the following syntax

```
"prog_structure":
{
"ch7": "[X, 10, X, 10, X, 10]",
"ch6": "[Y]"
} 
```
The body of "prog_structure" is also a dictionary, where the keys are the channel name (0 to 7), and the values are strings representing the pulse sequence. 
1. The pulse sequence must be presented in lists
2. You can call the name of waveforms you want the waveform generator to produce 
3. If you want to wait between pulses, simply insert a number. This number is in units of numbers of clock cycles, i.e. 2.6ns

You are also allowed to define looped arguments by the following syntax

```
"prog_structure":
{
"ch7": "[loop(3, [X, 10])]",
"ch6": "[Y]"
}
```
This program is exactly the same as the previous one. The loop function takes in two arguments, the first one is a loop count, and the second one is the pulse sequence to loop over, this pulse sequence is another list. The compiler also supports nested loops. 



### Tutorial jupyter notebook

You can play with _tutorial.ipynb_ to explore the various functionalities.  

