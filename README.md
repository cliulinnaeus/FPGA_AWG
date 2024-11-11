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

### Installation instructions
Follow the quick start guide in QICK repository but do not run the installation jupyter notebook _000_Install_qick_package.ipynb_ in _qick_demos_: [QICK qick start guide](https://github.com/openquantumhardware/qick/tree/main/quick_start)






