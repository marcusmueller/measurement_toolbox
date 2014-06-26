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

import pickle
import os
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import tarfile
import subprocess

class execution_agent_base(object):
    """
    base class for execution agents.
    """
    
    def __init__(self):
        self.channel = channel
        self.receiving = False
    def parse_command(self, cmd_dict):
        cmd = cmd_dict["command"]
        if "kwargs" in cmd_dict:
            kwargs = pickle.loads(cmd_dict["kwargs"])
        else:
            kwargs = dict()
        if "args" in cmd_dict:
            args = pickle.loads(cmd_dict["args"])
        else:
            args = []
        method = getattr(self,cmd)
        return method(*args, **kwargs)

    def stop_receiving(self):
        self.receiving = False

    def start_receiving(self):
        self.receiving = True
        channel.send( os.path.abspath(os.curdir) )
        while self.receiving:
            msg = channel.receive()
            result = self.parse_command(msg)
            channel.send(result)

class bootstrap_agent(execution_agent_base):
    """
    agent able to unpack a tar archive (e.g. containing an OOT module)

    """
    
    def __init__(self):
        execution_agent_base.__init__(self)
        self.path = "."

    def check_import(self, import_module):
        try:
            print "importing "+import_module
            __import__(import_module)
            return True
        except ImportError as e:
            return False
        return "WTF"
    
    def receive_file_stream(self, filename, file_content):
        file_obj = open(os.path.join(self.path, filename), "w")
        file_obj.write(file_content)
        file_obj.close()
        return os.path.abspath( file_obj.name )

    def send_file(self, path):
        path = os.path.join(self.path, path)
        return open(path).read()

    def set_path(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)
            if not os.path.isdir(path):
                return False
        self.path = path
        os.chdir(path)
        return os.path.abspath(path)

    def is_readable(self, path):
        return os.path.exists(path)

    def unpack_tar(self, tar):
        memfile = StringIO.StringIO(tar)
        tar = tarfile.open(fileobj = memfile, mode = "r")
        mem0_name = os.path.abspath(os.path.join(self.path, tar.members[0].name))
        tar.extractall(path = self.path)
        return mem0_name
    
    def get_cmd_output(self, cmd):
        return subprocess.check_output(cmd, shell=True)



def select_agent(classname):
    agentclass = globals()[classname]
    agent = agentclass()
    agent.start_receiving()

if __name__ == "__channelexec__":
    select_agent(channel.receive())
else:
    class DummyChannel(object):
        def send(self, string):
            print string
        _count = 0
        _vals = [ {"command": "check_import", "args": pickle.dumps(["numpy"])} ]

        def receive(self):
            if self._count < len(self._vals):
                self._count += 1
                return self._vals[self._count-1]
            return ""
    channel = DummyChannel()
