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
import benchmarking_task

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
        self.range_spec = (0,1,1000)
        self.ref_task_grc = {
                "class_name":"class",
                "module_name":"module",
                "instruction":"run_grc",
                "attributes": {
                    "range_test_variable":  { 
                        "param_type":  "LIN_RANGE",
                        "value": list(self.range_spec),
                        "value_type": "float64"
                        },
                    "list_test_variable": {
                        "param_type":  "LIST",
                        "value": [10,20,30],
                        "value_type": "int64"
                        },
                    "static_test_variable": {
                        "param_type":  "STATIC",
                        "value": float(numpy.pi),
                        "value_type": "float32"
                        }
                    },
                "sinks": [ ]
                }
        self.xml_file = open(os.path.join(os.path.dirname(__file__), "extraction_test_topblock.grc"), "r")
        self.ref_task_grc["grcxml"] = self.xml_file.read()
        self.xml_file.close()

    def tearDown(self):
        pass
    
    def test_001_instantiation(self):
        ra = remote_agent.remote_agent("tcp://0.0.0.0:12121")
        self.assert_(ra is not None)
        ra.ctx.destroy()
        time.sleep(1e-2)

    def test_002_grc(self):
        ra = remote_agent.remote_agent("tcp://0.0.0.0:"+str(numpy.random.randint(12000,13000)))
        mytask = benchmarking_task.task.from_dict(self.ref_task_grc)
        mytask.read_sinks_from_grc()
        ra.execute_all(mytask)
        ra.ctx.destroy()
        time.sleep(1e-2)


if __name__ == '__main__':
    gr_unittest.run(qa_remote_agent, "qa_remote_agent.xml")
