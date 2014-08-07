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

import benchmarking_task
import helpers
import tempfile

from gnuradio import gr, gr_unittest
try:
    import mtb_swig as mtb
except ImportError:
    pass

import numpy
import json
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

class qa_benchmarking_task (gr_unittest.TestCase):
    def setUp(self):
        self.taskstring = ""
        self.task = []
        self.range_spec = (0,1,1000)
        self.ref_task_dic = {
                "class_name":"class",
                "module_name":"module",
                "instruction":"run_fg",
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
                "sinks": ["myhumblesink",]
                }
    def tearDown(self):
        pass

    def test_001_param_range(self):
        p = benchmarking_task.parametrization(benchmarking_task.LIN_RANGE, self.range_spec)
        vals  = p.get_values()
        self.assertListEqual(vals.tolist(), numpy.linspace(*self.range_spec).tolist())
    def test_002_param_split_list_integer(self):
        N = 100
        SPLITS = 10
        p = benchmarking_task.parametrization(benchmarking_task.LIST, range(N))
        splitted = p.split(SPLITS)
        for i in range(SPLITS):
            self.assertSequenceEqual(range(i*(N/SPLITS), (i+1)*(N/SPLITS)), splitted[i].get_values())

    def test_003_param_split_list_non_integer(self):
        N = 100
        SPLITS = 11
        p = benchmarking_task.parametrization(benchmarking_task.LIST, range(N))
        splitted = p.split(SPLITS)
        total = numpy.concatenate([sp.get_values() for sp in splitted])
        self.assertListEqual(total.tolist(), range(N))
    def test_004_param_split_range(self):
        r = numpy.linspace(*self.range_spec)
        p = benchmarking_task.parametrization(benchmarking_task.LIN_RANGE, self.range_spec)
        splitted = p.split(13)
        for spl in splitted:
            l = len(spl.get_values())
            self.assert_(l >= len(r)/13 and l <= len(r)/13 + 1)
        total = numpy.concatenate([spl.get_values() for spl in splitted])
        ref_spec = list(self.range_spec)
        ref_spec[2] = (self.range_spec[2] / 13 ) * 13 + 13
        self.assertFloatTuplesAlmostEqual(total, numpy.linspace(*ref_spec), places = 5)

    def test_005_task_json_save(self):
        task = benchmarking_task.task("class", "module")
        task.set_parametrization("static_test_variable", 
            benchmarking_task.parametrization(benchmarking_task.STATIC,numpy.pi, numpy.dtype("float32").type))
        task.set_parametrization("range_test_variable", 
            benchmarking_task.parametrization(benchmarking_task.LIN_RANGE, self.range_spec) )
        task.set_parametrization("list_test_variable", 
            benchmarking_task.parametrization(benchmarking_task.LIST, [10,20,30], int) )
        task.sinks = self.ref_task_dic["sinks"]
        outfile = tempfile.NamedTemporaryFile(delete=False,suffix=".json")
        task.save(outfile)
        outfile.close()
        infile = open(outfile.name)
        resdic = json.load(infile)
        self.assert_(helpers.comp_dict(resdic, self.ref_task_dic))
        infile.close()

    def test_006_task_json_load(self):
        task = benchmarking_task.task.from_dict(self.ref_task_dic)
        outfile = StringIO.StringIO()
        task.save(outfile)
        outfile.seek(0)
        resdic = json.load(outfile)
        self.assert_(helpers.comp_dict(resdic, self.ref_task_dic))

    def test_007_task_grc_load(self):
        task = benchmarking_task.task.from_grc("extraction_test_topblock.grc")
        refdic = {
                "class_name": "", 
                "module_name": "", 
                "instruction": "run_fg", 
                "attributes": {
                    "length": {
                        "value_type": "float64", 
                        "param_type": "STATIC", 
                        "value": 100
                        }, 
                    "value": {
                        "value_type": "float64", 
                        "param_type": "STATIC", 
                        "value": 0.5
                        }
                    },
                "sinks": [ "blocks_vector_sink_x_0", ]
                }
        self.assert_(helpers.comp_dict(task.to_dict(), refdic))
    
    def test_008_total_points(self):
        task = benchmarking_task.task()
        l_noise     = 100
        l_signal    = 13
        task.set_parametrization("noise_power",  benchmarking_task.parametrization(benchmarking_task.LIST, range(l_noise), int))
        task.set_parametrization("signal_power", benchmarking_task.parametrization(benchmarking_task.LIN_RANGE, (0,10,l_signal)))
        task.set_parametrization("sample_rate", benchmarking_task.parametrization())
        task.set_parametrization("threshold", benchmarking_task.parametrization(benchmarking_task.STATIC, 1.0/numpy.pi))

        points = task.get_total_points()
        self.assertEqual(points, l_noise*l_signal * 1 * 1)

        n = 20

        tasks = task.split(n)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(sum([t.get_total_points() for t in tasks]), points)

    def test_009_grid(self):
        task = benchmarking_task.task()
        ns = [5, 7, 13]
        for n in ns:
            task.set_parametrization("var_range_"+str(n), benchmarking_task.parametrization(benchmarking_task.LIN_RANGE, (0,1,n)))
        ns.append(2)
        task.set_parametrization("var_list", benchmarking_task.parametrization(benchmarking_task.LIST, [0,1]))
        ns.append(1)
        task.set_parametrization("var_static", benchmarking_task.parametrization(benchmarking_task.STATIC, numpy.pi))

        total_should = reduce(lambda x,y: x*y, ns, 1)
        grid, constants, names = task.get_parameter_set()
        self.assertEqual(len(grid) , total_should)
        self.assertSequenceEqual(constants, [task.variables["var_static"].get_values()])

if __name__ == '__main__':
    gr_unittest.run(qa_benchmarking_task, "qa_benchmarking_task.xml")
