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

import execnet
import json
import pickle
import execution_agent
import os
import urllib2
import hashlib
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import ConfigParser

class dispatcher(object):
    """ A dispatcher using execnet to put work elsewhere """

    default_settings = """
    { "hosts": 
        [ { "address": "", "user": "" ,"key": "", "method": "ssh"} ]
    }
    """

    def __init__(self, settings = None):
        if settings is None:
            settings = self.default_settings
        if type(settings) is file:
            self.conf = json.load(settings)
        elif type(settings) is str: 
            self.conf = json.loads(settings)
        elif type(settings) is dict:
            self.conf = settings
        else:
            raise(TypeError("settings must be None, JSON string or JSON-parseable file"))
        self.gateways = execnet.Group()
        self.gws = []
        for json_host in self.conf["hosts"]:
            self.add_gateway(json_host)

    def add_gateway(self, host_dict=dict()):
        gw_spec = ""
        if type(host_dict) is str:
            host_dict = { "address" : host_dict}
            print host_dict
        if "spec" in host_dict:
            gw_spec = spec
        elif not "address" in host_dict or host_dict["address"] == "":
            gw = self.gateways.makegateway()
            host_dict["home_dir"] = os.path.expanduser("~")
            print "added local interpreter"
        else:
            if not "method" in host_dict:
                host_dict["method"] = "ssh"

            if host_dict["method"] == "ssh":
                if "user" in host_dict:
                    addr = "{user}@{address}".format(user = host_dict["user"], address = host_dict["address"])
                else:
                    addr = host_dict["address"]

                if "key" in host_dict:
                    gw_spec = "ssh=-i {key} {addr}".format(key = host_dict["key"], addr = addr)
                else:
                    gw_spec = "ssh={addr}".format(addr = addr)
            else:
                    gw_spec = "{method}={addr}".format(method = host_dict["method"], addr = host_dict["address"])
            gw = self.gateways.makegateway(gw_spec)

        channel =  gw.remote_exec(execution_agent)

        channel.send("bootstrap_agent")
        if "home_dir" in host_dict:
            home_dir = host_dict["home_dir"] 
            print "ignoring login dir {ldir} because {hdir} is set as home directory".format(
                    ldir = channel.receive(), hdir = host_dict["home_dir"])
            channel.send( make_command("set_path", home_dir) )
            print channel.receive()
        else:
            home_dir = channel.receive()
        host_dict["home_dir"] = home_dir
        host_dict["prefix"] = host_dict.get("prefix", os.path.join(home_dir, "prefix"))
        host_dict["channel"] = channel
        host_dict["spec"] = gw_spec
        self.gws.append(host_dict)



    def terminate_all(self):
        for gw in self.gws:
            gw.terminate()
        self.gws = []

    def _send_all(self, msg, gws = None):
        if gws is None:
            gws = self.gws
        for gw in gws:
            channel = gw["channel"]
            channel.send(msg)

    def _receive_all(self, gws = None):
        if gws is None:
            gws = self.gws
        return [ gw["channel"].receive() for gw in gws ]



    def check_gnuradio(self, gws = None):
        if gws is None:
            gws = self.gws
        command = make_command("check_import", "gnuradio")
        for gw in gws:
            gw["channel"].send(command)
            gw["has_gr"] = gw["channel"].receive()

        return [ gw["has_gr"] for gw in self.gws ]
    
    def send_file(self, file_obj, gws):
        command = make_command("receive_file_stream", 
                os.path.basename( file_obj.name ), file_obj.read()  )
        self._send_all(command, gws)
        return self._receive_all()
    def get_file(self, path, gws):
        command = make_command("send_file", path)
        self._send_all(command, gws)
        return self._receive_all()

    def send_archive(self, file_or_filename, archive_name = None, gws = None, force=False):
        if gws is None:
            gws = self.gws
        if hasattr(file_or_filename, "read"):
            file_contents = file_or_filename.read()
            if  archive_name is None:
                archive_name = getattr(file_or_filename, "name", "unknown")
        else:
            file_contents = open(file_or_filename).read()
            if archive_name is None:
                archive_name = os.path.basename(file_or_filename)
        tar_cmd = make_command("unpack_tar", file_contents)

        root_dirs = []
        for gw in gws:
            home = gw["home_dir"]
            channel = gw["channel"]
            path_cmd = make_command("set_path", os.path.join(home, "archives") )
            channel.send(path_cmd)
            path = channel.receive()
            channel.send(tar_cmd)
        for gw in gws:
            member0=channel.receive()
            root_dirs.append(member0)
            if not archive_name is None:
                gw[archive_name + "_root"] = member0

        return root_dirs

    def get_output(self, cmd, gws = None):
        """
        a delegate for subprocess.check_output
        """
        command = make_command( "get_cmd_output", cmd) 
        self._send_all(command, gws)
        return self._receive_all(gws)

    def dispatch_gr_benchmark(self, url="https://github.com/osh/gr-benchmark/archive/master.tar.gz", gws = None): 
        tar_f = get_online_file(url)
        rootdirs = self.send_archive(tar_f, "gr_benchmark", gws)

    def make_build_dirs(self, module_dir, gws = None):
        if gws is None:
            gws = self.gws
        for gw in gws:
            builddir = os.join(gw["home_dir"], "archives", module_dir, "build")
            cmd = make_command("set_path", builddir)
            gw["channel"].send(cmd)
        return self._receive_all()
    def cd_homedir(self, gws = None):
        if gws is None:
            gws = self.gws
        for gw in gws:
            cmd = make_command("set_path", gw["home_dir"])
            gw.send(cmd)
        return self._receive_all()
    def ensure_gnuradio(self):
        """
        checks whether GNU Radio is installed. Downloads and runs PyBOMBS on the machines that don't have it.
        """
        is_installed = self.check_gnuradio()
        missings = filter(lambda gw: not gw.get("has_gr", False), self.gws)
        if not len(missings):
            return True
        print "missing:"
        print missings

        
        pybombs_archive = get_online_file("https://github.com/pybombs/pybombs/archive/master.tar.gz")
        print "sending archives"
        pybombs_roots = self.send_archive(pybombs_archive, "pybombs", missings)
        for gw in missings:
            #gw["pybombs_root"] = "/home/marcus/archives/pybombs-master"
            path_cmd = make_command("set_path", gw["pybombs_root"])
            gw["channel"].send(path_cmd)
            root = gw["channel"].receive()
            print "root pybombs dir: ", root
            gw["pybombs_root"] = root
            get_default_cmd = make_command("send_file", os.path.join(root, "config.defaults"))
            print "ordering defaults"
            gw["channel"].send(get_default_cmd)

        for gw in missings:
            conf = ConfigParser.RawConfigParser()
            defaults_string = gw["channel"].receive()
            config_string = defaults_string.replace("[defaults]", "[config]")
            conf.readfp(StringIO.StringIO(config_string))
            conf.set("config", "prefix", gw["prefix"])
            conf.set("config", "satisfy_order", "src") #can't install a thing on these machines!
            outfile = StringIO.StringIO()
            conf.write(outfile)
            command = make_command("receive_file_stream", 
                os.path.join(gw["pybombs_root"], "config.dat"), outfile.getvalue())
            gw["channel"].send(command)
        for gw in missings:
            gw["channel"].receive()
        print "current directories"
        return self.get_output("./pybombs install gnuradio", missings)

def make_command(method, *args, **kwargs):
    dct = {"command": method}
    if not args is None:
        dct["args"] = pickle.dumps(args)
    if not kwargs is None:
        dct["kwargs"] = pickle.dumps(kwargs)
    return dct

def get_online_file(url):
    """
    returns content of the file as seekable file-like object
    """
    try:
        os.makedirs("cache")
    except OSError:
        pass

    try:
        f = open("url.cache", "r")
        cachejson = json.load(f)
        f.close()
    except IOError:
        cachejson = {}
    try:
        cachefilename = cachejson[url]
        cachefile = open(cachefilename, "r")
        return cachefile
    except KeyError as e:
        cachejson[url] = os.path.join("cache", hashlib.md5(url).hexdigest())
        newfile = open(cachejson[url], "w")
        newfile.write(urllib2.urlopen(url).read())
        newfile.close()
        f = open("url.cache", "w")
        json.dump(cachejson, f)
        return open(cachejson[url], "r")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-c","--config")
    parser.add_argument("-f", "--file")
