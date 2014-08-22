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

from gnuradio import gr, gr_unittest
try:
    import mtb_swig as mtb
except ImportError:
    pass

import numpy
import os
import time
import json
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class qa_remote_agent (gr_unittest.TestCase):
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
    def tearDown(self):
        pass
    def test_001_run_task(self):
        tempstore = StringIO.StringIO()
        results = self.ra.execute_all(self.task, tempstore)
        for result in results:
            par = result.parameters
            res = result.results
            self.assertEqual(len(par),2)
            self.assertEqual(len(res),1)
            self.assert_(par["value"])
            self.assert_(par["length"])
            self.assertEqual(par["length"], len(res["blocks_vector_sink_x_0"]))
        self.assertSequenceEqual(json.loads(tempstore.getvalue()), [r.to_dict() for r in results])




if __name__ == '__main__':
    gr_unittest.run(qa_remote_agent, "qa_remote_agent.xml")
