#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2014 Marcus Müller.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import remote_agent
import helpers
import benchmarking_task as bt
from result import result, result_comprehension
from gnuradio import gr, gr_unittest
try:
    import mtb_swig as mtb
except ImportError:
    pass

import numpy
import os
import time
import json
import tempfile
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class qa_result (gr_unittest.TestCase):
    def setUp(self):
        self.taskstring = ""
        self.task = []
        self.range_spec = (0,1,100)
        self.ref_task_json = \
        """
{"class_name": "extraction_test_topblock", "module_name": "mtb", "instruction": "run_fg", "sinks": ["blocks_vector_sink_x_0"], "attributes": {"length": {"value_type": "float64", "param_type": "LIST", "value": [1.0, 10.0, 100.0, 1000.0]}, "value": {"value_type": "float64", "param_type": "LIN_RANGE", "value": [1.0, 10.0, 100.0]}}}
        """
        self.task = bt.task.load(self.ref_task_json)
        self.ra = remote_agent.remote_agent()
        self.tempdir = tempfile.mkdtemp("results")
        tempstore = open(os.path.join(self.tempdir, "result.json"), "w")
        results = self.ra.execute_all(self.task, tempstore)
        tempstore.close()
        self.rc1 = result_comprehension()
        self.rc1.load_directory(self.tempdir)
    def tearDown(self):
        pass
    def test_001_load_results(self):
        self.assertSequenceEqual(sorted(self.rc1.parameters), sorted(["length", "value"]))
        self.assertSequenceEqual(sorted(self.rc1.variables), sorted(["blocks_vector_sink_x_0"]))
    def test_002_test_values(self):
        means = numpy.array(self.rc1.get_variable_over_parameter("blocks_vector_sink_x_0", "value"))
        self.assertFloatTuplesAlmostEqual(means[:,0], means[:,1],places = 5)




if __name__ == '__main__':
    gr_unittest.run(qa_result, "qa_result.xml")
