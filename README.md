# QICK-AWG: Flexible Arbitrary Waveform Generation for Experimental Setups
### (More documentations will be added)
QICK-AWG is a specialized software package that transforms a QICK-based FPGA into an Arbitrary Waveform Generator (AWG) designed to integrate seamlessly into diverse experimental setups. Many labs already equipped with experiment control hardware and software face challenges integrating QICK without substantial modifications, as QICK is a self-contained and specialized library. QICK-AWG bridges this gap by enabling QICK-based FPGA boards to function solely as AWGs, concentrating on generating customizable pulse sequences for flexible waveform generation. This program is suitable for doing complex dynamical decoupling sequences in atomic, molecular, optical (AMO) experiments such as the NV-centers. 

Built on top of the QICK library, this codebase provides a straightforward programming interface. When deployed, the FPGA operates as an AWG, actively listening for and responding to user commands through a network socket. Note that this initial version does not yet support in situ pulse parameter sweep, which is a planned update in future versions.

Note: 
- This software has only been tested on ZCU111. One may run into unexpected bugs on other QICK boards (ZCU216, RFSoC4x2)
- This software does not yet support in situ pulse parameter sweeps, which can be used to realize adiabatic passage sequences. This is a planned update in future versions.
- This software is still yet a work in progress. Please report any bugs to me. 

See the original QICK repository at: https://github.com/openquantumhardware/qick

## Installation

### Prerequisites
It is assumed you start with a brand new ZCU111 board. If you have an old board with already installed newest version of QICK, you may want to consider downgrading it. 

For PYNQ disk image, it is recommended to use v2.6 (this code based has only been tested on v2.6)
For QICK version, it is required to use an older version (0.2.191 works), as QICK-AWG will not work on the newest version in the QICK repo. You can find an older (and working) version of QICK [here](https://github.com/yao-lab-harvard/qick). Clone this repository into your FPGA. 

You also need a client computer to be connect to the same LAN of the FPGA. 

### Installation instructions
This package needs to be downloaded on both the QICK board and the client computer. 

#### Installation on the QICK board
Follow the quick start guide in QICK repository but do not run the installation jupyter notebook _000_Install_qick_package.ipynb_ in _qick_demos_: [QICK qick start guide](https://github.com/openquantumhardware/qick/tree/main/quick_start)

Use your favorite shell program (I typically use GitBash), ssh into the FPGA address, e.g.
```
ssh xilinx@192.168.0.123
```
the password is _xilinx_ 

Now type 
```
ls jupyter_notebooks
```
and you should see a repository called _qick_ being listed. cd into this repository
```
cd jupyter_notebooks/qick
```
Evoke root access (the QICK library can only be ran under root access, which means it has to be installed under root)
```
su
```
enter password _xilinx_. You should now see the new line should initiate with _root@pynq:_

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
python3 test_FPGA_AWG.py
```
This initializes a server object on the FPGA and it actively listens to commands send to it.



