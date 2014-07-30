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
                    type(None): lambda x: dict(),
            }


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
