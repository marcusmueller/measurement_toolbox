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


import zmq
import json
import threading
import execnet
import remote_agent
import helpers

class distributor(object):
    """
    Uses JSON-stored remote list to run gr-benchmark on these machines.
    
    Internally heavily based on zeroMQ.
    """

    config = { "push_bind":     "tcp://127.0.0.1:{port:d}",
               "pub_bind":      "tcp://127.0.0.1:9010",
               "result_bind":   "tcp://127.0.0.1:9009",
               "start_pub_port": 10001,
             }
    def __init__(self, cfg = None):
        self.ctx = zmq.Context.instance
        self.ctx()
        self._started = False
        self.pools = dict()
        self.workers = dict()
        self._worker_lock = threading.Lock()
        self._results_lock = threading.Lock()
        self._config_lock = threading.Lock()
        self._tasks = set()
        if not cfg is None:
            self.load_config(cfg)
        self.publisher = self.ctx().socket(zmq.PUB)
        self.publisher.bind(self.config["pub_bind"])
        self.result_listener = self.ctx().socket(zmq.PULL)
        self.result_listener.bind(self.config["result_bind"])
        self.max_pub_port = self.config["start_pub_port"]
        self.result_thread = threading.Thread(target=lambda : self.results_loop())
        self.result_thread.daemon = True
        self.receiving = True
    def start(self):
        self.result_thread.start()
    def __del__(self):
        self.ctx().destroy()
    
    def add_pool(self, pool_id):
        if not pool_id in self.pools:
            self._config_lock.acquire()
            sock = self.ctx().socket(zmq.PUSH)
            self.max_pub_port += 1
            bind_addr = self.config["push_bind"].format(port=self.max_pub_port) 
            sock.bind(bind_addr)
            self.pools[pool_id] = (sock, bind_addr, set())
            self._config_lock.release()
        return self.pools[pool_id]
    def issue_command(self, worker_id, cmd):
        if type(worker_id) == str:
            worker = self.workers[worker_id]
        else:
            worker = worker_id
        
    def load_config(self, config):
        self._config_lock.acquire()
        self.config.update(helpers.x_to_dict[type(config)](config))
        self._config_lock.release()
    def load_workers(self, workers):
        print "loading"
        workers_dict = helpers.x_to_dict[type(workers)](workers)
        for worker in workers_dict["workers"]:
            worker.setdefault("exec_id",0)
            ## if not configured to be in a pool, have a pool of your own.
            pool_id = worker.setdefault("pool", [worker["id"]])
            ctrl_sock = self.ctx().socket(zmq.REQ)
            ctrl_lock = threading.Lock()
            ctrl_lock.acquire()
            self.workers[worker["id"]] = (ctrl_sock, ctrl_lock, worker)
            if "execnet_address" in worker:
                channel = execnet.makegateway(worker["execnet_address"]).remote_exec(remote_agent)
                channel.send(worker["control_address"])
            #print "{id:s}: connecting to {control_address:s}...".format(**worker)
            ctrl_sock.connect(worker["control_address"])
            #print worker["id"], "connected"

            self._send_ctrl(worker, {"instruction":"set_attr","attr":"name", "value": worker["id"]})
            ctrl_lock.release()
            pool = self.add_pool(pool_id)
            pool[2].add(worker["id"])
            ctrl_lock.acquire()
            self._send_ctrl(worker, {"instruction": "task_attach", "remote": pool[1]})
            self._send_ctrl(worker, {"instruction": "results_attach", "remote": self.config["result_bind"]})
            ctrl_lock.release()
            ctrl_lock.acquire()
            ctrl_lock.release()
    def _send_ctrl(self, worker, dic):
        exec_id = worker["exec_id"]
        sock = self.workers[worker["id"]][0]
        dic["id"] = exec_id
        sock.send_json({"cmd":[dic,]})
        worker["exec_id"]+=1
        return sock.recv_json()
    
    def execute_task(self, task):
        print "loaded task with  {:d} total items".format(task.get_total_points())
        print "have {:d} pools with {:s} workers".format(len(self.pools), ";".join([ str(len(p[-1])) for p in self.pools.values()]))
        for poolname in self.pools:
            socket, bind_addr, set_of_workers = self.pools[poolname]
            n_workers = len(set_of_workers)
            splittasks = task.split(n_workers)
            print "dealing with pool {name:s}, having {n_workers:d} workers.".format(
                    name = poolname, n_workers = n_workers)
            for worker, workload in zip(set_of_workers, splittasks):
                workload = workload.to_dict()
                worker_dic = self.workers[worker][2]
                workload["id"] = str(worker_dic["exec_id"]) + str(worker)
                socket.send_json([workload])
                worker_dic["exec_id"] += 1

    def load_tasks(self, tasks):
        tasks_dict = helpers.x_to_dict[type(tasks)](tasks)
        for task in tasks_dict["tasks"]:
            target = task["target"]
            items = task["items"]
            socket, address, list_of_remotes = self.pools[target]
            for item in items:
                socket.send_json(item)
                ###FIXME###
                # Extend to logical items, ie. one item representing 100 steps
                # of flowgraph parameter variation and thus, 100 tasks for the
                # pool; nothing easier than that using numpy's broadcasting and
                # grid abilities.

    def results_loop(self):
        print "starting to receive results..."
        self._started = True
        self._results_lock.acquire()
        try:
            while True: #will exit when _results_lock.release()d
                print self.result_listener.recv_json()
        except zmq.error.ContextTerminated as c:
            pass

    def running(self):
        return self._started

    def shutdown_all(self):
        for w_id in self.workers.keys():
            sock, lock, worker = self.workers[w_id]
            lock.acquire()
            self._send_ctrl(worker, {"instruction": "stop"} )
            #deliberately not cleaning up locks!
        self._results_lock.release()
        print "shut down."
