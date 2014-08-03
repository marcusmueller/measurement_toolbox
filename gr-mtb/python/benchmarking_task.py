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

import helpers

import os
import numpy
import json
import copy

from gnuradio import gr
try:
    try:
        from grc.python.Platform import Platform
    except ImportError:
        from gnuradio.grc.python.Platform import Platform
except ImportError as e:
    pass
    # can work without grc on remote nodes.

_type_strings = ("DONT_SET", "STATIC", "LIN_RANGE", "LIST")
_task_strings = ("RUN_FG", "RUN_GRC", "OTHER")

for stringpack in (_type_strings, _task_strings):
    locals().update(map(reversed,enumerate(stringpack)))

class task(object):
    """
    representation of a benchmarking task
    """
    def __init__(self, class_name_or_grc="", module_name = None, task_type = RUN_FG):
        self.variables = {}
        self.set_type(task_type)
        if task_type == RUN_FG:
            self.class_name = class_name_or_grc
            self.module_name = module_name
        elif task_type == RUN_GRC:
            self.grcxml = class_name_or_grc

    @staticmethod
    def load(f_or_fname):
        """
        load from file object or filename
        """
        dic = helpers.load_from_json(f_or_fname)
        return task.from_dict(dic)

    @staticmethod
    def from_string(string):
        """
        parse JSON string
        """
        dic = json.loads(string)
        return task.from_dict(dic)

    @staticmethod
    def from_dict(dic):
        """
        use dict to initialize task
        """
        instruction = dic["instruction"].upper()
        if _task_strings.index(instruction) == RUN_FG:
            class_name = dic.get("class_name")
        elif _task_strings.index(instruction) == RUN_GRC:
            class_name = dic.get("grc_file")
        module_name = dic.get("module_name",None)
        task_ = task(class_name, module_name, _task_strings.index(instruction))
        for var, paramdic in dic["attributes"].items():
            task_.variables[var] = parametrization.from_dict(paramdic)
        return task_

    @staticmethod
    def from_grc(filename):
        """
        read .grc file to extract variables
        """
        platform = Platform()
        data = platform.parse_flow_graph(filename)

        fg = platform.get_new_flow_graph()
        fg.import_data(data)
        fg.grc_file_path = os.path.abspath(filename)
        fg.validate()

        if not fg.is_valid():
            raise StandardError("Compilation error")
        _task = task("","")
        for var in fg.get_variables():
            _task.set_parametrization(var.get_id(), parametrization(STATIC, var.get_var_value()))
        return _task



    def set_type(self, type=RUN_FG):
        self._task_type = type
        self.instruction = _task_strings[type].lower()

    def set_target_flowgraph(self, target):
        if issubclass(target, gr.top_block):
            self.class_name = target.__name__
            self.module_name = target.__module__
            self.target = target
        else:
            raise TypeError()

    def get_variables_from_target_class(self):
        setters = filter(lambda s: s.startswith("set_"), self.target.__dict__.keys())
        return [ setter[4:] for setter in setters]

    def set_parametrization(self, variable, parametrization):
        self.variables[variable] = parametrization

    def save(self, f_or_fname):
        dic = self.to_dict()
        helpers.save_to_json(dic, f_or_fname)
    def to_dict(self):
        dic = { "instruction": self.instruction }
        if self.instruction == "run_fg":
            dic.update( {"class_name":  self.class_name,
                         "module_name": self.module_name
            } ) 
            dic["attributes"] = {}
            for var,param in self.variables.items():
                dic["attributes"][var] = param.to_dict()
        return dic
    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
    def __repr__(self):
        return json.dumps(self.to_dict())
    
    def _get_const_names(self):     return filter(lambda k: self.variables[k].param_type == STATIC, self.variables.keys())
    def _get_variable_names(self):  return filter(lambda k: self.variables[k].param_type in (LIN_RANGE, LIST), self.variables.keys())
    def get_parameter_set(self):
        """
        construct the measurement space and return it.

        This constructs the measurement space and returns it.

        Return Values
        -------------
        (var_grid, constants, names):

        var_grid -- a grid of measurement points that cover all combinations of variables as specified in the parametrizations
        constants -- the values of constants 
        names -- the names of the respective variables in the order that they are contained in [ var_grid, constants ]
        """
        
        varying_names   = self._get_variable_names()
        const_names     = self._get_const_names()
        names   = varying_names + const_names
        varying = [self.variables[name] for name in varying_names]
        const   = [self.variables[name] for name in const_names]
        mesh    = numpy.meshgrid(*[var.get_values() for var in varying])
        var_grid = numpy.transpose([numpy.ravel(ndarray) for ndarray in mesh])
        return var_grid, const, names

    def split(self, n):
        """
        returns a split of the parametrization space into n subtasks, done along the biggest sub-problem dimension
        """
        max_param = max(self.variables, key = lambda k: self.variables[k].get_length())
        param_splits = self.variables[max_param].split(n)
        task_splits  = [task(task_type = self._task_type) for i in param_splits]
        for i,t in enumerate(task_splits):
            if self._task_type == RUN_FG:
                t.class_name  = self.class_name
                t.module_name = self.module_name
            elif self._task_type == RUN_GRC:
                t.grcfile = self.grcfile
            for varname in self.variables.keys():
                if varname == max_param:
                    t.set_parametrization(varname, param_splits[i])
                else:
                    t.set_parametrization(varname, self.variables[varname])
        return task_splits

    def get_total_points(self):
        """
        returns the total amount of measurement points defined in this task.
        """
        return reduce(lambda x,y: x * (y.get_length()), self.variables.values(), 1)
        ### Whoa. Never thought my python would be this functional at one point. fischerm would be kind of irritated I didn't
        ### switch to haskell by now.

class parametrization(object):
    def __init__(self, param_type=DONT_SET, value=None, value_type=float):
        """description of a parametrization.

        param_type -- one of {DONT_SET,STATIC,LIN_RANGE,LIST}
        value -- the corresponding value
        value_type -- type to ensure when setting the individual parametrization; especially useful when wanting to use integers from a range.

        For LIN_RANGE, value should be a tuple following the pattern of
            (start, stop, n_step)
        Compare the numpy.linspace documentation for details
        """
        self.param_type = param_type
        self._val = value
        self._val_type = value_type
        if  (param_type in [LIST, LIN_RANGE] and not hasattr(value, "__iter__")) or \
            (param_type is LIN_RANGE and len(value) != 3):
            raise ValueError("if using LIST or LIN_RANGE, value needs to be iterable; for range, value must be (start, stop, n_step)")
    @staticmethod
    def from_dict(dic):
        return parametrization(_type_strings.index(dic["param_type"]), value = dic["value"], value_type = numpy.dtype(dic["value_type"]))

    def split(self,n_partitions):
        """Generates a list of new parametrizations.

        These parametrizations are even parts of the given range or list.
        
        In case of LIN_RANGE, if the range's number of steps is not an integer
        multiple of partitions, the steps are set to the next bigger integer
        multiple of n_partitions, enabling even splitting.

        In case of LIST, m = floor( len(value) / n_partitions) elements are
        assigned to every partition, and the first 
        len(value) - m * n_partitions partitions get 1 element additionally.
        
        In case of STATIC and DONT_SET, a list containing n_partitions of the
        original function is returned.
        """
        partitions = int(n_partitions)
        if self.param_type == DONT_SET or self.param_type == STATIC:
            return [self,] * partitions
        if self.param_type == LIST:
            m = len(self._val) / partitions
            larger = len(self._val) - m * partitions
            ret_partitions = []
            start = 0
            for i in xrange(partitions):
                if i < larger:
                    n = m + 1
                else:
                    n = m
                ret_partitions.append(
                    parametrization(
                        param_type=LIST,
                        value=self._val[start:start+n],
                        value_type = self._val_type
                    )
                )
                start += n
            assert(start == len(self._val))
            return ret_partitions
        elif self.param_type == LIN_RANGE:
            l_r = self._val[2] # length of range
            if l_r % partitions: # not a multiple
                l_r += partitions - (l_r %partitions)
            n = l_r / partitions
            (start, stop) = self._val[:2]
            r_tot = stop - start
            r_indiv = (r_tot * (1.0 + 1.0 / l_r ) )  / partitions
            step = r_indiv / n 
            return [ parametrization( 
                    LIN_RANGE,
                    (start + r_indiv * i, 
                    start + r_indiv * (i+1) - step,
                    n ), self._val_type )
                for i in xrange(partitions) ]

    def get_values(self):
        """
        returns a list of the actual values contained.
        """
        if self.param_type == STATIC:
            return [self._val_type(self._val)]
        if self.param_type == LIST:
            return map(self._val_type, self._val)
        if self.param_type == LIN_RANGE:
            if not numpy.dtype(self._val_type) == numpy.dtype(float):
                return numpy.array(numpy.linspace(*self._val), dtype = self._val_type)
            else:
                return numpy.linspace(*self._val)

    def get_length(self):
        return  {
                    STATIC:     lambda: 1,
                    DONT_SET:   lambda: 1,
                    LIST:       lambda: len(self._val),
                    LIN_RANGE:  lambda: self._val[2]
                }[self.param_type]()

    def to_dict(self):
        dic =   {
                "param_type":   _type_strings[self.param_type],
                "value_type":   numpy.dtype(self._val_type).name,
                "value":        helpers.convert_to_dict(self._val) if self.param_type in [LIST,LIN_RANGE,STATIC] else self._val
                }
        return dic
    def __eq__(self, other):
        return  (self.param_type == other.param_type) and\
                (self._val_type == other._val_type) and\
                (self._val == other._val)
    def __repr__(self): return str(self.to_dict())
