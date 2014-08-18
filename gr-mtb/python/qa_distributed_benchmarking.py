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

import distributed_benchmarking
import benchmarking_task as bt
import remote_agent
import helpers

import copy
import json
import numpy
import os
import subprocess
import sys
import tempfile
import time


from gnuradio import gr, gr_unittest
try:
    import mtb_swig as mtb
except ImportError:
    pass

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class qa_distributed_benchmarking (gr_unittest.TestCase):
    def setUp(self):
        self.range_spec = (0,1,100)
        self.xml_file = open(os.path.join(os.path.dirname(__file__), "extraction_test_topblock.grc"), "r")

        self.xml_file.close()
        task = bt.task.from_grc(self.xml_file.name)
        task.set_parametrization("length", bt.parametrization(bt.LIST, [2,5,10], int))
        task.set_parametrization("value", bt.parametrization(bt.LIN_RANGE, (0,10,20)))
        
        print task._get_variable_names()
        print task.variables["length"]

        self.dis = distributed_benchmarking.distributor()
        self.dis.start()
        time.sleep(0.05)
        self.worker_dic = {
                "id": "worker",
                "control_address": "tcp://127.0.0.1:",
                "pool": "default"
                }
    def tearDown(self):
        pass
    def test_001_start(self):
        self.assertFalse(self.dis._results_lock.acquire(False))
        ws =[]
        for i in range(1):
            worker = copy.copy(self.worker_dic)
            worker["id"] += str(i)
            worker["control_address"] += str(8787 + i)
            ws.append(worker)
            subprocess.Popen(["python", "remote_agent.py", worker["control_address"]])
            print "spawned {:d}. subprocess".format(i)
#        for i in range(5):
#            ws[i]["pool"] = str(i)
        workers = {"workers":ws}
        print "loading.."
        time.sleep(1)
        self.dis.load_workers(workers)
        time.sleep(1)
        print "done"

        #task = bt.task.from_dict(self.ref_task_grc)
        task = bt.task.from_grc(self.xml_file.name)
        self.dis.execute_task(task)

        self.dis.shutdown_all()
        self.assert_(self.dis._results_lock.acquire(False))
        time.sleep(0.1)
        self.dis.ctx().destroy()

if __name__ == '__main__':
    if not os.getenv("MALLOC_CHECK_"):
        print "DIRTY WORKAROUND HOTFIX WARNING"
        print "python double frees std::strings that it already printed on exit on my system. I don't know why, the internet is full of this bug, but it's very hard to nail down. However, you can make the incredibly long trace go away by \"export MALLOC_CHECK_=4\""
        time.sleep(2)
    gr_unittest.run(qa_distributed_benchmarking)#, "qa_distributed_benchmarking.xml")
