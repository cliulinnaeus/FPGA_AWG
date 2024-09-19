(More documentations will be added)
Code for running an arbitrary waveform generator on the Xilinx ZCU111 FPGA based on Qick (https://github.com/openquantumhardware/qick)

In many labs with already built experiment control hardware and software, it is nontrivial to directly integrate a Qick-based FPGA into this network as Qick is a very self-contained library. To do so requires a programming interface from the Qick to the external control software. 

This code base is built on top of Qick and serves as programming interface to the Qick library. When the code is ran on the FPGA, the FPGA behaves like a server that actively listens to commands sent by the user via a network socket. The FPGA behaves like an arbitrary waveform generator (AWG) sitting at the other end of the network socket. It does not (yet) have the ability to perform measurements but is merely a programmable AWG. 

The compiler is also rewritten. The users can now define a pulse sequence more straightforwardly (to be shown below). The compiler now generates Qick assembly v1 code differently from before to reduce the number of register writes during the firing of pulses. 





