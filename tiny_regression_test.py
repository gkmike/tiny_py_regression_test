import sys
import os
import argparse
import subprocess as sub
import copy
import threading

class test_base:
    def __init__(self, name):
        self._name = name
        self._skip = False
        self._parent = None
        self._event = threading.Event()
        self._wait_test = None
        self._status = ""
    def get_cwd(self):
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()
    def get_name(self):
        return self._name
    def set_skip(self):
        self._skip = True
        self._status = "(skipped)"
    def get_status(self):
        return self._status
    def after(self, test):
        self._wait_test = test
        return self

class regression_test(test_base):
    def __init__(self, top_name):
        super().__init__(top_name)
        self._tests = []
    def create_test(self, test_name):
        t = test(test_name)
        t._parent = self
        self._tests.append(t)
        return t
    def show_test(self):
        print(self.get_name() + " [test list]")
        for t in self._tests:
            print (t.get_name() + ": " + t.get_status() + " [test] [path=" + t.get_cwd() + "]")
            for j in t._jobs:
                print("    " + j.get_name() + ": " + j.get_status() + " [job] [path=" + j.get_cwd() + "]")
    def process(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', help='run all test')
        parser.add_argument('-t', '--test', nargs='*', help='run the specified test only')
        parser.add_argument('-j', '--job', nargs='*', help='run the specified job only')
        args = parser.parse_args()
        if len(sys.argv) == 1:
            self.show_test()
            parser.print_help()
            return
        for t in self._tests:
            if args.test:
                if t.get_name() not in args.test:
                    t._skip = True
                    t._event.set()
            if args.job:
                for j in t._jobs:
                    if j.get_name() not in args.job:
                        j._skip = True
                        j._event.set()
        self.show_test()
        threads = []
        for t in self._tests:
            if not t._skip: 
                th = threading.Thread(target=t._run)
                threads.append(th)
                th.start()
                
        for th in threads:
            th.join()
        print("DDDDDDDDDDDDDDDDDDDDDDDDDDD")
        self.show_test()
        #self._cwd_proc()
        #self._gen_pytest()
        #self._run_pytest()

class test(test_base):
    def __init__(self, test_name):
        super().__init__(test_name)
        self._jobs = []
    def create_job(self, job_name):
        j = job(job_name)
        j._parent = self
        self._jobs.append(j)
        return j
    def _run(self):
        if self._wait_test:
            print(self.get_name() + " waiting...")
            self._wait_test._event.wait()
        print("running test " + self.get_name())
        for j in self._jobs:
            if not j._skip: 
                j._run()
        self._event.set()
        

class job(test_base):
    def __init__(self, job_name):
        super().__init__(job_name)
        self.file = file()
        self.env = env()
        self.cmd = cmd()
    def _run(self):
        if self._wait_test:
            print(self.get_name() + " waiting...")
            self._wait_test._event.wait()
        print("running job " + self.get_name())
        cwd = self.get_cwd()
        sub.run('rm -rf ' + cwd, shell=True)
        sub.run('mkdir -p ' + cwd, shell=True)
        self.file._put(cwd)
        self.env._setup()
        ret = self.cmd._run(cwd)
        if ret == 0:
            self._status = "done"
        else:
            self._status = "fail (exit_code: " + str(ret) + ")"
        self._event.set()
    def copy_from(self, j):
        self.file = copy.deepcopy(j.file)
        self.env = copy.deepcopy(j.env)
        self.cmd = copy.deepcopy(j.cmd)
        return self

class file:
    def __init__(self):
        self.links = file_handles()
        self.copys = file_handles()
    def _put(self, cwd):
        self.links._put("ln -sf", cwd)
        self.copys._put("cp -rf", cwd)

class file_handles:
    def __init__(self):
        self._list = []
    def add(self, path):
        self._list.append(path)
        return self
    def _put(self, sh_cmd, cwd):
        for f in self._list:
            sub.run(sh_cmd + " " + os.path.abspath(f) + " .", shell=True, cwd=cwd)
            
class env:
    def __init__(self):
        self._env = {}
    def set(self, var, val):
        self._env[var] = str(val)
        return self
    def _setup(self):
        for k,v in self._env.items():
            os.environ[k] = v
        
class cmd():
    def __init__(self):
        self._steps = []
    def add(self, cmd):
        self._steps.append(cmd)
        return self
    def _run(self, cwd):
        for s in self._steps:
            s = sub.run(s, shell=True, cwd=cwd)
            if s.returncode != 0:
                return s.returncode
        return 0