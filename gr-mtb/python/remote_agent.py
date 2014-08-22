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
#import threading
import os
import sys
import tempfile
import time

import benchmarking_task as bt
import helpers
from result import result
## ugly hack to make things work with bpython et al.
## threading assumes that stdout/err/in behave like proper streams,
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
        
        self.blocks = {}


    def execute_all(self, task, storage=None):
        """
        execute all parametrizations as defined in task object

        Parameters
        ----------

        task -- the task which is broken down into the individual execution points
        storage -- if set to a string, will store the result in that path as JSON. If set to a file, will use that.

        Returns
        -------

        results -- the results of the computation in a list of result objects.
        """
        instruction =task._task_type
        #print "running a total number of points of", task.get_total_points()
        setters = {}
        if instruction == bt.RUN_FG:
            class_n = task.class_name
            time.sleep(1)
            module_n = str(task.module_name)
            module = __import__(module_n, fromlist = [ str(class_n) ])
            self.block_class = getattr(module, task.class_name)
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
        print "processing {:d} points".format(task.get_total_points())
        for inst, values in self.parameterize(task, self.block_class):
            datadict = self._execute(inst, task.sinks)
            results.append( result( values, datadict ))
        try:
            if storage and not hasattr(storage,"write") :
                outfile = open(str(storage), 'w')
                json.dump( [ r.to_dict() for r in results ] , outfile)
                outfile.close()
            elif storage:
                json.dump( [ r.to_dict() for r in results ] , storage)
        except IOError as e:
            print e
        return results

    def _execute(self, inst, sinks):
        inst.run()
        inst.wait()
        datadict = {}
        for sink in sinks:
            datadict[sink] = list(inst.__dict__[sink].data())
            #print "sink {:s} has data".format(sink), datadict[sink]
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

if __name__ == "__channelexec__":
    """
    execnet execution.
    Set up remote agent with specified control address.
    """

    agent = remote_agent(channel.receive())
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
#    parser.add_argument("CONTROL_ADDRESS")
    parser.add_argument("-t","--task", type=argparse.FileType('r'))
    parser.add_argument("-o","--output", type=argparse.FileType('w'), default='-')
    
    args = parser.parse_args()
    ra = remote_agent()
    if args.task:
        t = bt.task.load(args.task)
        res = ra.execute_all(t, args.output)
