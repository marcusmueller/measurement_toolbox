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

import json

x_to_dict = {       
                    dict:   lambda x: x,
                    list:   lambda x: x,
                    tuple:  lambda x: x,
                    set:    lambda x: x,
                    file:   json.load,
                    str:    json.loads,
                    float:  lambda x: x,
                    int:    lambda x: x,
                    type(None): lambda x: dict(),
            }

def comp_dict(dicta, dictb):
    """compares two dictionaries element-wise, including recursion through sub-dictionaries."""
    for key in dicta.keys():
        if isinstance(dicta[key], dict):
            if not comp_dict(dicta[key], dictb[key]):
                return False
        elif dicta[key] != dictb[key]:
            print dicta[key] , "!=", dictb[key]
            return False
    return True

def apply_to_type(dic, thing):
    return dic[type(thing)](thing)

def convert_to_dict(whatever):
    return apply_to_type(x_to_dict, whatever)

def save_to_json(obj, f_or_fname):
    if type(f_or_fname) is str:
        json.dump(obj, open(f, "w"))
    else:
        json.dump(obj, f_or_fname)

def load_from_json(f_or_fname):
    if type(f_or_fname) is str:
        return json.loads(f_or_fname)
    else:
        return json.load(f_or_fname)

class dictable(object):
    def __eq__(self, other): return helpers.comp_dict(self.to_dict(), other.to_dict())
    def __str__(self):       return json.dumps(self.to_dict(), indent=4)
    def __repr__(self): return json.dumps(self.to_dict())

