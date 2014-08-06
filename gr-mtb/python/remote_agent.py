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

import imp
import json
import multiprocessing
import os
import sys
import tempfile
import traceback
import zmq

import benchmarking_task as bt
from benchmarking_task import parametrization, task
import helpers
## ugly hack to make things work with bpython et al.
## multiprocessing assumes that stdout/err/in behave like proper streams,
## for some python shells some methods have not been implemented, though.

from gnuradio import gr
try:
    try:
        from grc.python.Platform import Platform
    except ImportError:
        from gnuradio.grc.python.Platform import Platform
except ImportError as e:
    pass
    # can work without grc on remote nodes.
try:
    _ = sys.stdout.flush
except AttributeError:
    sys.stdout.flush = lambda : None
try:
    _ = sys.stderr.flush
except AttributeError:
    sys.stderr.flush = lambda : None
try:
    _ = sys.stdin.close
except AttributeError:
    sys.stdin.close = lambda : None



class remote_agent(object):
    """
    started remotely, should connect to control
    """
    
    def __init__(self, control_address="tcp://0.0.0.0:6666"):
        self.ctrl_address = control_address
        self.name = control_address # for now
        self.modules = {}
        self.ctx = zmq.Context()
        self.control_rx = self.ctx.socket(zmq.REP)
        self.control_rx.bind(control_address)
        self.result_tx = self.ctx.socket(zmq.PUSH)
        self.task_rx = self.ctx.socket(zmq.PULL)
        self.broadcast_rx = self.ctx.socket(zmq.SUB)

        self.control_lock = multiprocessing.Lock()
        self.task_lock = multiprocessing.Lock()
        self.results_lock = multiprocessing.Lock()
        self.broadcast_lock = multiprocessing.Lock()
        
        self.control_thread = multiprocessing.Process(target = lambda : self.control_loop())
        self.task_thread = multiprocessing.Process(target = lambda : self.task_loop())
        self.broadcast_thread = multiprocessing.Process(target = lambda : self.broadcast_loop())
        
        self.blocks = {}

        self.cmd_dic = {
        "task_attach":  lambda x: self.task_attach(x),
        "results_attach":  lambda x: self.results_attach(x),
        "broadcast_attach":  lambda x: self.broadcast_attach(x),
        "assign_attr":  lambda x: setattr(self, x["attr"], x["value"]),
        "exec_file":    lambda x: execfile(x["filename"]),  ##OK, let's start to worry about security and authentication later on
        "addpath":      lambda x: sys.path.append(x["path"]),
        "stop":         lambda x: self.stop()
        }
        self.task_dic = {
        "run_fg":   lambda x: self.run_fg(x),
        "square":       lambda x: float(x["value"])**2
        }
        
        self.ctrl_active = True
        self.task_active = False
        self.broadcast_active = False

    def start(self):
#        self.control_thread.start()
        self.control_loop()


    def __del__(self):
        self.ctx.destroy()
    def parse_cmd(self, dct):
        """
        use the information stored in the dictionary
        """
        #print dct
        if "cmd" in dct:
            cmd_results = []
            commands = dct["cmd"]
            try:
                for command in commands:
                    instruction = command["instruction"]
                    try:
                        result = self.cmd_dic[instruction](command)
                        if result is None:
                            result = {"result": None}
                        cmd_results.append(result, command.get("id", 0))
                    except KeyError as e:
                        cmd_results.append({"result": "fail", "error": e.msg , "id": command.get("id", 0)})
            except:
                pass
            finally:
                print cmd_results
                self.control_rx.send_json(cmd_results)
        if "task" in dct:
            results = []
            tasks = dct["task"]
            for dct_task in tasks:
                task = task.from_dict(dct_task)
                self.execute_all(task)
            self.results_tx.send_json(results)

    def task_attach(self, task_dict):
        self.task_lock.acquire()
        self.task_rx.connect(task_dict["remote"])
        self.task_active = True
        self.task_lock.release()
        self.task_thread.start()
    def results_attach(self, task_dict):
        self.results_lock.acquire()
        self.results_tx.connect(result_dict["remote"])
        self.results_lock.release()
        return True
    def broadcast_attach(self, task_dict):
        self.broadcast_lock.acquire()
        self.broadcast_rx.connect(result_dict["remote"])
        self.broadcast_active = True
        self.broadcast_lock.release()
        self.broadcast_thread.start()

    def send_results(self, result, res_id = 0):
        self.results_lock.acquire()
        self.result["id"] = res_id
        self.result["origin"] = self.name
        self.results_tx.send_json(result)
        self.results_lock.release()

    def stop(self):
        self.control_lock.acquire()
        self.ctrl_active = False
        try:
            self.control_rx.close()
        except e:
            print e

    def control_loop(self):
        print "start"
        while self.ctrl_active:
            self.control_lock.acquire()
            cmd = self.control_rx.recv_json()
            self.parse_cmd(cmd)
            self.control_lock.release()
    def task_loop(self):
        while self.task_active:
            cmd = self.task_rx.recv_json()
            self.task_lock.acquire()
            self.parse_cmd(cmd)
            self.task_lock.release()
    def broadcast_loop(self):
        while self.broadcast_active:
            cmd = self.broadcast_rx.recv_json()
            self.broadcast_lock.acquire()
            self.parse_cmd(cmd)
            self.broadcast_lock.release()

    def run_fg(self, task_dict):
        """
        construct a flow graph of given name.
        """
        try:
            module = __import__(task_dict["module_name"], fromlist = [ task_dict["class_name"] ] )
            # I'm open for improved instantiation schemes
            self.block_class = getattr(module, task_dict["class_name"])
            block = block_class()
        except KeyError as e:
            raise e # handling later
        if "attributes" in task_dict:
            attr = task_dict["attributes"]
            for key in attr.keys():
                try:
                    setter = getattr(block, "set_"+key,)
                    setter(attr[key])
                except AttributeError as e:
                    # no setter defined; guessing this calls for just setting the instance member
                    setattr(block, key, attr[key])
                except Exception as e:
                    pass
        self.blocks[task_dict["id"]] = block
        block.run()
        sinks = {"id":task_dict["id"], "data" : {}}
        dct = block.__dict__
        for key in dct.keys():
            if "sink" in key and hasattr(dct[key], "to_basic_block"): # check whether GR block
                try:
                    sinks["data"][key] = dct[key].data()
                except TypeError as e: #either data is not a callable, or it has a different signature
                    pass
        return sinks
    def execute_all(self, task):
        """
        execute all parametrizations as defined in task object
        """
        instruction = task._task_type
        print "running at total number of points of", task.get_total_points()
        setters = {}
        if instruction == bt.RUN_FG:
            class_n = task.class_name
            module_n = task.module_name
            module = __import__(module_n, from_list = [ class_n ])
            self.block_class = getattr(module, task_dict["class_name"])
        elif instruction == bt.RUN_GRC:
            if not hasattr(self, "temp_outdir"):
                self.temp_outdir = tempfile.mkdtemp(suffix = "_py", prefix = "gr-mtb-")
            temp_grc_file  = tempfile.NamedTemporaryFile(suffix = ".grc", delete = False, dir = self.temp_outdir)

            temp_grc_file.write(task.grcxml)
            temp_grc_file.close()

            platform = Platform()
            data = platform.parse_flow_graph(temp_grc_file.name)

            fg = platform.get_new_flow_graph()
            fg.import_data(data)
            fg.grc_file_path = os.path.abspath(temp_grc_file.name)
            fg.validate()

            if not fg.is_valid():
                raise StandardError("Compilation error")
            class_n = fg.get_option("id")
            filepath = os.path.join(self.temp_outdir, class_n + ".py")
            gen = platform.get_generator()(fg, filepath)
            gen.write()

            module = imp.load_source(class_n, filepath)
            self.block_class = getattr(module, class_n)
            results = []
            for inst, values in self.parameterize(task, self.block_class):
                results.append( result( values, self._execute(inst, task.sinks)) )
            return results

    def _execute(self, inst, sinks):
        inst.run()
        inst.wait()
        datadict = {}
        for sink in sinks:
            datadict[sink] = inst.__dict__[sink].data()
        return datadict
        
                

    def _get_setters(self,task, instance):
        setters = {}
        for var, parametrization in task.variables.items():
            try:
                setter = getattr(instance, "set_"+var,)
                setters[var] = setter
            except AttributeError as e:
                # no setter defined; guessing this calls for just setting the instance member
                setters[var] = lambda v: setattr(instance, var, v)
            except Exception as e:
                pass
        return setters

    def parameterize(self, task, block_class):
        import time
        grid, constants, names = task.get_parameter_set()
        n_vars = len(grid[0])
        for param_set in grid:
            instance = block_class()
            setters = self._get_setters(task, instance)
            values = {}
            for idx, param_val in enumerate(param_set):
                var_name = names[idx]
                setters[var_name](param_val)
                values[var_name] = param_val
                #print "setting", var_name, param_val
            for idx, param_val in enumerate(constants):
                var_name = names[idx+n_vars]
                setters[var_name](param_val)
                values[var_name] = param_val
                #print "const", var_name, param_val
            yield (instance, values)

class result(helpers.dictable):
    def __init__(self, parameters, results):
        self.results = results
        self.parameters = parameters
    def to_dict(self):
        dic = {   "results": dict(self.results),
                    "parameters": dict(self.parameters),
                }
        return dic

if __name__ == "__channelexec__":
    """
    execnet execution.
    Set up remote agent with specified control address.
    """

    agent = remote_agent(channel.receive())
