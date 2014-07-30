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
try:
    from gnuradio import gr
except ImportError as e:
    pass

DONT_SET, STATIC, RANGE, LIST = range(4)

class task(object):
    """
    representation of a benchmarking task
    """
    RUN_FG, OTHER = range(2)
    def __init__(self, dct=None):
        self.__dict__.update(convert_to_dict(dct))
    def set_type(self, type=RUN_FG):
        if type == self.RUN_FG:
            self.variables = {}
            self.instruction = "run_fg"

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

    def set_variable_options(self, variable, options):
        self.variables[variable] = options

    def save(self, f_or_fname):
        dic = { "instruction": self.instruction}
        if self.instruction == "run_fg":
            dic.update( {"class_name":  self.class_name,
                         "module_name": self.module_name
            } ) 
            dic["attributes"] = { }
            dic["attributes"].update(self.variables)
        helpers.save_to_json(dic, f_or_fname) 

class parametrization(object):

    def __init__(self, param_type=DONT_SET, value=None, value_type=float):
        """description of a parametrization.

        param_type -- one of {DONT_SET,STATIC,RANGE,LIST}
        value -- the corresponding value
        value_type -- type to ensure when setting the individual parametrization; especially useful when wanting to use integers from a range.

        For RANGE, value should be a tuple following the pattern of
            (start, stop, n_step)
        Compare the numpy.linspace documentation for details
        """
        self.param_type = param_type
        self._val = value
        self._val_type = value_type
        if  (param_type in [LIST, RANGE] and not hasattr(value, "__iter__")) or \
            (param_type is RANGE and len(value) != 3):
            raise ValueError("if using LIST or RANGE, value needs to be iterable; for range, value must be (start, stop, n_step)")

    def split(self,n_partitions):
        """Generates a list of new parametrizations.

        These parametrizations are even parts of the given range or list.
        
        In case of RANGE, if the range's number of steps is not an integer
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
            m = len(value) / partitions
            larger = len(value) - m * partitions
            partitions = []
            start = 0
            for i in range(partitions):
                if i < larger:
                    n = m + 1
                else:
                    n = m
                partitions.append(
                    parametrization(
                        param_type=LIST,
                        value=self._val[start:start+n],
                        value_type = self.param_type
                    )
                )
                start += n
            assert(start == len(self._vals))
            return partitions
        elif self.param_type == RANGE:
            l_r = self._val[2] # length of range
            if l_r % partitions: # not a multiple
                l_r += partitions - (l_r %partitions)
            n = l_r / partitions
            (start, stop) = self._val[:2]
            r_tot = stop - start
            r_indiv = float(r_tot) / partition
            return [ parametrization( RANGE, (start + r_indiv * i, start + r_indiv * (i+1), n ), self._val_type ) for i in range(partitions) ]
