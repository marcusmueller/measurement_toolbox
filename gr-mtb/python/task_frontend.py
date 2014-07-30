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
        

        self.connect(self.gui.open_json, QtCore.SIGNAL("activated()"), lambda: self.load_json())
        self.connect(self.gui.save_json, QtCore.SIGNAL("activated()"), lambda: self.save_json())
        self.connect(self.gui.import_tb, QtCore.SIGNAL("activated()"), lambda: self.import_tb())
        self.connect(self.gui.import_grc, QtCore.SIGNAL("activated()"), lambda: self.import_grc())
        self.gui.show()


    def load_json(self):
        self.json_fname = QtGui.QFileDialog.getOpenFileName(self, 'Open JSON file', filter='JSON file (*.json *.js *.task)')
    def save_json(self):
        self.json_fname = QtGui.QFileDialog.getSaveFileName(self, 'Save JSON file', filter='JSON file (*.json *.js *.task)')
        pass
    def import_tb(self):
        pass
    def import_grc(self):
        pass

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ui = TaskFrontend()
    sys.exit(app.exec_())
