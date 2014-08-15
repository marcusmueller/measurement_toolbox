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
import task_frontend
import helpers
import benchmarking_task

from gnuradio import gr, gr_unittest
try:
    import mtb_swig as mtb
except ImportError:
    pass

import gc
import json
import numpy
import os
import tempfile
import time
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
from PyQt4 import QtGui
from PyQt4 import QtCore

class MyApplicationClass(QtGui.QApplication):

  started = QtCore.pyqtSignal()

  def exec_(self):
      self.started.emit()
      return QtGui.QApplication.exec_()

class qa_task_frontend (gr_unittest.TestCase):
    def setUp(self):
        self.taskstring = ""
        self.task = []
        self.range_spec = (0,1,100)
        self.ref_task_grc = {
                "class_name":"class",
                "module_name":"module",
                "instruction":"run_grc",
                "attributes": {
                    "value":  { 
                        "param_type":  "LIN_RANGE",
                        "value": list(self.range_spec),
                        "value_type": "float64"
                        },
                    "length": {
                        "param_type":  "LIST",
                        "value": [10,20,30],
                        "value_type": "int64"
                        },
                    },
                "sinks": [ "blocks_vector_sink_x_0" ]
                }
        self.xml_file = open(os.path.join(os.path.dirname(__file__), "extraction_test_topblock.grc"), "r")
        self.ref_task_grc["grcxml"] = self.xml_file.read()
        self.xml_file.close()
        self.jsonfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.jsonfilename = self.jsonfile.name
        json.dump(self.ref_task_grc, self.jsonfile)
        self.jsonfile.close()
        self.qapp = MyApplicationClass([])

    def tearDown(self):
        os.unlink(self.jsonfilename)


    def test_001_load_json_file(self):
        self.my_ui = task_frontend.TaskFrontend()
        self.my_ui._load_json_file_direct(self.jsonfilename)

if __name__ == '__main__':
    gr_unittest.run(qa_task_frontend)#, "qa_task_frontend.xml")
