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

import sys
import imp
import os
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4 import uic
import numpy

import benchmarking_task as bt
from benchmarking_task import task, TYPE_STRINGS
import helpers

class TaskFrontend(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        pathcandidates = [os.path.curdir, os.path.join(os.path.pardir, "qt"), os.path.join(imp.find_module("mtb")[1], "qt")]

        self.gui = None
        for path in pathcandidates:
            try:
                uifile = os.path.join(path, "task_frontend.ui")
                self.gui = uic.loadUi(uifile)
                print "loaded "+uifile
                break
            except IOError:
                pass
        if self.gui is None:
            raise IOError("could not find task_frontend.ui")        
        self.__lastrow = -1
        self.__lastvar = None
        self.__enable_cell_checks = False
        self.__enable_sink_checks = False
        
        for s in TYPE_STRINGS:
            self.gui.param_type.addItem(s)
        self.connect(self.gui.open_json, SIGNAL("activated()"), lambda: self.load_json_file())
        self.connect(self.gui.save_json, SIGNAL("activated()"), lambda: self.save_json_file())
        self.connect(self.gui.import_tb, SIGNAL("activated()"), lambda: self.import_tb())
        self.connect(self.gui.import_grc, SIGNAL("activated()"), lambda: self.import_grc())
        self.connect(self.gui.variable_table, SIGNAL("cellClicked(int,int)"), lambda row, col: self._cell_clicked(row,col))
        self.connect(self.gui.variable_table, SIGNAL("cellActivated(int,int)"), lambda row, col: self._cell_clicked(row,col))
        self.connect(self.gui.variable_table, SIGNAL("cellChanged(int,int)"), lambda row, col: self._cell_changed(row,col))
        self.connect(self.gui.sink_table, SIGNAL("cellChanged(int,int)"), lambda row, col: self._sink_changed(row,col))
        self.connect(self.gui.add_button, SIGNAL("clicked()"), lambda: self._add_var())
        self.connect(self.gui.add_sink_button, SIGNAL("clicked()"), lambda: self._add_sink())
        self.connect(self.gui.del_sink_button, SIGNAL("clicked()"), lambda: self._del_sink())
        self.connect(self.gui.param_type, SIGNAL("currentIndexChanged(int)"), lambda idx: self._type_changed(idx))
        self.gui.show()
        self.task = task()
        self.__enable_cell_checks = True

    def _fill_from_task(self):
        num_rows = len(self.task.variables)
        self.gui.variable_table.setRowCount(num_rows)
        for idx, (key, param) in enumerate(self.task.variables.items()):
            self._add_row_from_parametrization(idx, key, param)
        self.gui.sink_table.setRowCount(len(self.task.sinks))
        for idx, sink in enumerate(self.task.sinks):
            self._add_row_from_sink(idx,sink)

    def _add_row_from_parametrization(self, row, name, param):
        self.__enable_cell_checks = False
        param_dic = param.to_dict()
        print name+": {param_type}={value}({value_type})".format(**param_dic)
        #self.gui.variable_table.add
        widgets = []
        widgets.append(QtGui.QTableWidgetItem( name ) )
        for k in ["param_type", "value", "value_type"]:
            widgets.append(QtGui.QTableWidgetItem( str(param_dic[k])))
        widgets[1].setFlags(widgets[1].flags() &  ~Qt.ItemIsEditable)

        for col, widget in enumerate(widgets):
            self.gui.variable_table.setItem(row, col, widget)
        self.__enable_cell_checks = True

    def _add_row_from_sink(self, row, sink):
        self.__enable_sink_checks = False
        self.gui.sink_table.setItem(row,0, QtGui.QTableWidgetItem(sink))
        self.__enable_sink_checks = True

    def _cell_clicked(self, row, col):
        print row, col
        if row == self.__lastrow:
            return
        var_name = self.gui.variable_table.item(row, 0).text()
        self.__lastrow = row
        self.__lastvar = str(var_name)
        self.__enable_cell_checks = False
        self._description_fill(var_name)
        self.__enable_cell_checks = True

    def _description_fill(self, qvar_name):
        var_name = str(qvar_name)
        self.gui.param_id.setText(qvar_name)
        var = self.task.variables[var_name]
        #print "selected ", var_name, TYPE_STRINGS[var.param_type]
        self.gui.param_type.setCurrentIndex(var.param_type)

    def _cell_changed(self, row, col):
        if not self.__enable_cell_checks:
            return
        var_name = self.gui.variable_table.item(row, 0).text()
        if col == 0: #variable name changed!
            if not self.__lastvar is None:
                self.task.variables[str(var_name)] = self.task.variables.pop(self.__lastvar)
                print "renamed", self.__lastvar, "to", var_name
                self._description_fill(str(var_name))
        elif col == 2: #setter spec changed!
            correct = self._setter_spec_change(str(var_name), str(self.gui.variable_table.item(row,2).text()))
            color = Qt.black if correct else Qt.red 
            self.gui.variable_table.item(row,col).setForeground(color)
            self._description_fill(var_name)
        else:
            pass

    def _sink_changed(self, row, col):
        if not self.__enable_sink_checks:
            return
        self.task.sinks = []
        for row in range(self.gui.sink_table.rowCount()):
            self.task.sinks.append(str(self.gui.sink_table.item(row,0).text()))

    def _setter_spec_change(self, var_name, spec):
        var = self.task.variables[var_name]
        if var.param_type == bt.DONT_SET:
            var._val = str(spec)
            return True
        if var.param_type == bt.STATIC:
            try:
                val = float(str(spec))
                var._val = val
                return True
            except:
                return False
        if var.param_type in [ bt.LIST , bt.LIN_RANGE ]:
            try:
                val = eval(str(spec)) #THIS IS SPARTAAAA
                print var_name,"...", val
                iter(val)
                print "got iter."
                if var.param_type == bt.LIN_RANGE:
                    l = len(val)
                    print "length", l
                    if l != 3:
                        return False
                    var._val = list([float(x) for x in val])
                    return True
                else:
                    var._val = list([var._val_type.type(x) for x in val])
                    return True
            except:
                return False
        print "huh", var.param_type

    def _type_changed(self, type):
        if not self.__enable_cell_checks:
            return
        varname = str(self.gui.param_id.text())
        self.task.variables[varname].param_type = type
        self.gui.variable_table.item(self.__lastrow, 1).setText(bt.TYPE_STRINGS[type])
        self._cell_changed(self.__lastrow, 2) #highlight if type doesn't fit value
        

    def _add_var(self):
        newname = "new_variable{:d}"
        counter = 0
        while newname.format(counter) in self.task.variables:
            counter += 1
        newname = newname.format(counter)
        newvar = bt.parametrization()
        self.task.variables[newname] = newvar
        n_rows = self.gui.variable_table.rowCount()
        self.gui.variable_table.setRowCount(n_rows+1)
        self._add_row_from_parametrization(n_rows,newname, newvar)
    def _add_sink(self):
        newname = "new_vector_sink{:d}"
        counter = 0
        while newname.format(counter) in self.task.sinks:
            counter += 1
        newname = newname.format(counter)
        self.task.sinks.append(newname)
        n_rows = self.gui.sink_table.rowCount()
        self.gui.sink_table.setRowCount(n_rows+1)
        self._add_row_from_sink(n_rows, newname)
    def _del_sink(self):
        col = 0
        row = self.gui.sink_table.currentRow()
        sinkname = str(self.gui.sink_table.item(row,col).text())
        self.gui.sink_table.removeRow(row)
        self.task.sinks.remove(sinkname)

    def load_json_file(self):
        self.json_fname = QtGui.QFileDialog.getOpenFileName(self, 'Open JSON file', filter='JSON file (*.json *.js *.task)')
        print self.json_fname
        self._load_json_file_direct(self.json_fname)
        
    def _load_json_file_direct(self, fname):
        self.task = task.from_dict(helpers.load_from_json(file(fname)))
        self._fill_from_task()
        
    def save_json_file(self):
        self.json_fname = QtGui.QFileDialog.getSaveFileName(self, 'Save JSON file', filter='JSON file (*.json *.js *.task)')
        self.task.save(str(self.json_fname))
    def import_tb(self):
        #FIXME
        pass
    def import_grc(self):
        self.grc_fname = QtGui.QFileDialog.getOpenFileName(self, 'Open GRC file', filter='GRC Flowgraph (*.grc)')
        self._import_grc_direct(self.grc_fname)
    def _import_grc_direct(self, name):
        self.task = bt.task.from_grc(name)
        self._fill_from_task()

