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

from mtb import *

workers = {
     "workers": [
        {"id": "firstborn", "control_address": "tcp://127.0.0.1:9990", "pools" : ["firstpool"], "execnet_address" : ""} ,
        {"id": "second", "control_address": "tcp://127.0.0.1:9991", "pools" : ["firstpool"], "execnet_address" : ""} ,
        {"id": "third", "control_address": "tcp://127.0.0.1:9992", "pools" : ["firstpool"], "execnet_address" : ""} ,
        {"id": "second", "control_address": "tcp://127.0.0.1:9993", "execnet_address" : ""} ,
        ]
     }
tasks = {
     "tasks": [
        {"target": "firstpool", "items":[
            {"instruction": "square", "value": 10.0} ,
            {"instruction": "square", "value": 20.0} ,
            {"instruction": "square", "value": 30.0} ,
            {"target": "firstpool", "instruction": "run_fg", "module_name": "mtb", "block_name": "extraction_test_topblock",
        "attributes": {"value" :3.141, "length" : 1000}}
        ],}
        ]
    }
dis = distributor()
dis.load_workers(workers)
dis.load_tasks(tasks)
dis.shutdown_all()
