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
from PyQt4 import uic

from benchmarking_task import task
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
        

        self.connect(self.gui.open_json, QtCore.SIGNAL("activated()"), lambda: self.load_json_file())
        self.connect(self.gui.save_json, QtCore.SIGNAL("activated()"), lambda: self.save_json_file())
        self.connect(self.gui.import_tb, QtCore.SIGNAL("activated()"), lambda: self.import_tb())
        self.connect(self.gui.import_grc, QtCore.SIGNAL("activated()"), lambda: self.import_grc())
        self.gui.show()
        self.task = task()

    def _fill_from_task(self):
        num_rows = len(self.task.variables)
        self.gui.variable_table.setRowCount(num_rows)
        for idx, (key, param) in enumerate(self.task.variables.items()):
            param_dic = param.to_dict()
            print key+": {param_type}={value}(value_type)".format(**param_dic)
            #self.gui.variable_table.add
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
        pass
    def import_grc(self):
        pass

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ui = TaskFrontend()
    sys.exit(app.exec_())
