#!/usr/bin/env python
##################################################
# Gnuradio Python Flow Graph
# Title: Extraction Test Topblock
# Generated: Thu Jun 26 13:00:39 2014
##################################################

from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser

class extraction_test_topblock(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Extraction Test Topblock")

        ##################################################
        # Variables
        ##################################################
        self.value = value = 0.5
        self.length = length = 100

        ##################################################
        # Blocks
        ##################################################
        self.blocks_vector_sink_x_0 = blocks.vector_sink_f(1)
        self.blocks_head_0 = blocks.head(gr.sizeof_float*1, int(length))
        self.analog_const_source_x_0 = analog.sig_source_f(0, analog.GR_CONST_WAVE, 0, 0, value)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_const_source_x_0, 0), (self.blocks_head_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_vector_sink_x_0, 0))



    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value
        self.analog_const_source_x_0.set_offset(self.value)

    def get_length(self):
        return self.length

    def set_length(self, length):
        self.length = length
        self.blocks_head_0.set_length(int(self.length))

if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
    tb = extraction_test_topblock()
    tb.start()
    tb.wait()
