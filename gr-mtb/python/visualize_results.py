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

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import Qwt5 as Qwt
from PyQt4 import uic
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QColor
import argparse
import imp
import numpy
import os
import scipy.io
import sys
import time

import benchmarking_task as bt
from benchmarking_task import task, TYPE_STRINGS
from result import result, result_comprehension
import helpers

class VisualizeResults(QtGui.QMainWindow):
    #colorset = ( QColor.blue, QColor.red, QColor.yellow, QColor.cyan, QColor.magenta, QColor.green)
    colorset = ( "blue", "red", "yellow", "cyan", "magenta", "green" )
    export_dict = {"Matlab":"mat", "CSV":"csv"}
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        pathcandidates = [os.path.curdir, os.path.join(os.path.pardir, "qt"), os.path.join(imp.find_module("mtb")[1], "qt")]

        self.gui = None
        for path in pathcandidates:
            try:
                uifile = os.path.join(path, "visualize_results.ui")
                self.gui = uic.loadUi(uifile)
                print "loaded "+uifile
                break
            except IOError:
                pass
        if self.gui is None:
            raise IOError("could not find visualize_results.ui")        

        self._vars_selected = False

        self.gui.PlotArea.insertLegend(Qwt.QwtLegend())
        self.connect(self.gui.actionLoad, SIGNAL("activated()"), lambda: self.load_results())
        #self.connect(self.gui.actionSave, SIGNAL("activated()"), lambda: self.load_results())
        self.connect(self.gui.ParameterList, SIGNAL("itemSelectionChanged()"), lambda : self._parameter_activated())
        self.connect(self.gui.ExportButton, SIGNAL("clicked()"), lambda: self.export())

        self.rc = result_comprehension()
        self.gui.show()

    def load_results(self):
        p = str(QtGui.QFileDialog.getExistingDirectory(self, "Load results form directory"))
        self.rc.load_directory(p)
        self.fill_from_result_comprehension()
    
    def fill_from_result_comprehension(self):
        self.gui.VariableList.setRowCount(len(self.rc.variables))
        self.gui.ParameterList.setRowCount(len(self.rc.parameters))
        for idx,variable in enumerate(sorted(self.rc.variables)):
            var_item = QtGui.QTableWidgetItem(str(variable))
            var_item.setFlags(var_item.flags() &  ~Qt.ItemIsEditable)
            function_item = QtGui.QTableWidgetItem("")
            self.gui.VariableList.setItem(idx, 0, var_item)
            self.gui.VariableList.setItem(idx, 1, function_item)
        for idx,param in enumerate(sorted(self.rc.parameters)):
            param_item = QtGui.QTableWidgetItem(str(param))
            param_item.setFlags(param_item.flags() &  ~Qt.ItemIsEditable)
            filter_item = QtGui.QTableWidgetItem(str(""))
            self.gui.ParameterList.setItem(idx, 0, param_item)
            self.gui.ParameterList.setItem(idx, 1, filter_item)

    def _parameter_activated(self):

        if not len(self.gui.VariableList.selectedItems()):
            if self._vars_selected:
                self._clear_all_curves()
            self._vars_selected = False
            self._enable_export(False)
            for item in self.gui.ParameterList.selectedItems():
                item.setForeground(Qt.black)
            self.gui.ParameterList.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

            self.gui.PlotArea.setAxisTitle(Qwt.QwtPlot.xBottom, '')
            self.gui.PlotArea.setAxisTitle(Qwt.QwtPlot.yLeft, '')
            ## Plot the selected parameters
            rows = set([idx.row() for idx in self.gui.ParameterList.selectedIndexes()])
            if not len(rows):
                return
            selected_params = [str(self.gui.ParameterList.item(row, 0).text()) for row in rows]
            for att in self.gui.PlotArea.itemList():
                if not str(att.title) in selected_params:
                    att.detach()
                else:
                    selected_params.pop(str(att.title()))
            for row, param in enumerate(selected_params):
                param_values = self.rc.get_parameter_values(param)
                curve = Qwt.QwtPlotCurve(param)
                color = self.colorset[row % len(self.colorset)]
                pen = QtGui.QPen(QtGui.QColor(color))
                pen.setWidth(1)
                curve.setPen(pen)
                curve.attach(self.gui.PlotArea)
                curve.setData(range(len(param_values)), param_values)
            self.gui.PlotArea.replot()
        else:
            self._clear_all_curves()
            self._vars_selected = True
            self.gui.ParameterList.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            if len(set([idx.row() for idx in self.gui.ParameterList.selectedIndexes()])) != 1:
                self._enable_export(False)
                return
            self._enable_export(True)
            rows = set([idx.row() for idx in self.gui.VariableList.selectedIndexes()])
            selected_variables = [str(self.gui.VariableList.item(row, 0).text()) for row in rows]
            selected_parameter_row = self.gui.ParameterList.selectedIndexes()[0].row()
            selected_parameter = str(self.gui.ParameterList.item(selected_parameter_row,0).text())
            self.gui.PlotArea.setAxisTitle(Qwt.QwtPlot.xBottom, selected_parameter)
            self.gui.PlotArea.setAxisTitle(Qwt.QwtPlot.yLeft, ",".join(selected_variables))
            for idx, var in enumerate(selected_variables):
                pairs = self.rc.get_variable_over_parameter(var, selected_parameter)
                array = numpy.array(pairs)
                curve = Qwt.QwtPlotCurve(var)
                color = self.colorset[idx % len(self.colorset)]
                pen = QtGui.QPen(QtGui.QColor(color))
                pen.setWidth(1)
                curve.setPen(pen)
                curve.attach(self.gui.PlotArea)
                curve.setData(array[:,0], array[:,1])
            self.gui.PlotArea.replot()
    def _clear_all_curves(self):
        for att in self.gui.PlotArea.itemList():
             att.detach()
    def _enable_export(self, enable=True):
        self.gui.FormatSelection.setEnabled(enable)
        self.gui.ExportButton.setEnabled(enable)

    def export(self, exportfile = None, fmt="CSV"):
        rows = set([idx.row() for idx in self.gui.VariableList.selectedIndexes()])
        selected_variables = [str(self.gui.VariableList.item(row, 0).text()) for row in rows]
        if not exportfile:
            fmt = str(self.gui.FormatSelection.currentText())
            fname = str(QtGui.QFileDialog.getSaveFileName(self, 'Save {:s} file'.format(fmt), filter='{fmt:s} file (*.{suff:s}])'.format(fmt=fmt,suff=self.export_dict[fmt])))
        if len(set([idx.row() for idx in self.gui.ParameterList.selectedIndexes()])) != 1:
            return
        rows = set([idx.row() for idx in self.gui.VariableList.selectedIndexes()])
        selected_parameter_row = self.gui.ParameterList.selectedIndexes()[0].row()
        selected_parameter = str(self.gui.ParameterList.item(selected_parameter_row,0).text())
        arr = self.rc.get_variables_over_parameter(selected_variables, selected_parameter)
        if fmt == "CSV":
            numpy.savetxt(fname, arr, delimiter=";", header = selected_parameter+";"+";".join(selected_variables))
        elif fmt == "Matlab":
            ex_dic = {selected_parameter:arr[:,0]}
            for idx, var in selected_variables:
                ex_dic[var] = arr[:,idx+1]
            scipy.io.savemat(fname, ex_dic)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", default=None)
    args = parser.parse_args()
    app = QtGui.QApplication(sys.argv)
    ui = VisualizeResults()
    if args.directory:
        ui.rc.load_directory(args.directory)
        ui.fill_from_result_comprehension()
    sys.exit(app.exec_())

