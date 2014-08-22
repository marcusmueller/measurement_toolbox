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
import json
import os
import numpy

class result(helpers.dictable):
    def __init__(self, parameters, results):
        self.results = results
        self.parameters = parameters

    def to_dict(self):
        dic = {   "results": dict(self.results),
                    "parameters": dict(self.parameters),
                }
        return dic

    @staticmethod
    def from_file(f):
        results = json.load(f)
        if type(results) == list:
            return [ result( **r ) for r in results ]
        else:
            return result(**results)


class result_comprehension(object):
    def __init__(self):
        self.variables = set()
        self.parameters = set()
        self.results = set()
    def load_file(self, fname):
        f = open(fname)
        results = result.from_file(f)
        f.close()
        for res in results:
            self.results.add(res)
            self.parameters.update(res.parameters.keys())
            self.variables.update(res.results.keys())
    def load_directory(self, directory):
        for filename in filter(lambda name: name.endswith('json'), os.listdir(directory)):
            self.load_file(os.path.join(directory,filename))
    
    def get_variable_over_parameter(self, variable, parameter, constraint = lambda x: True, apply_function=numpy.mean):
        if not variable in self.variables or not parameter in self.parameters:
            raise ValueError("can't find variable or parameter")
        pairs = []
        for res in self.results:
            try:
                param_value = res.parameters[parameter]
                if not constraint(res.parameters):
                    continue
                var_value = apply_function(res.results[variable])
                pairs.append((param_value, var_value))
            except KeyError:
                pass
        return sorted(pairs, key=lambda pair: pair[0])
    def get_variables_over_parameter(self, variables, parameter, constraint = lambda x: True, apply_function=numpy.mean):
        mat = []
        for res in self.results:
            try:
                param_value = res.parameters[parameter]
                if not constraint(res.parameters):
                    continue
                var_values = [apply_function(res.results[variable]) for variable in variables]
                row = [param_value]
                row += var_values
                mat.append(row)
            except KeyError:
                pass
        return numpy.array(sorted(mat, key=lambda row: row[0]))

    def get_parameter_values(self, parameter, constraint = lambda x: True):
        values = []
        for res in self.results:
            try:
                param_value = res.parameters[parameter]
                if constraint(res.parameters):
                    values.append(param_value)
            except KeyError:
                pass
        return numpy.array(sorted(values))               
        
