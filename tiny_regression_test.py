import sys
import os
import argparse
import subprocess as sub
import copy

class test_base:
    def __init__(self, name):
        self._name = name
        self._skip = False
        self._parent = None
    def get_cwd(self):
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()
    def get_name(self):
        return self._name
    def get_status(self):
        if self._skip:
            return " (skipped)"
        return ""

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
            print (t.get_name() + t.get_status() + " [test] [path=" + t.get_cwd() + "]")
            for j in t._jobs:
                print("    " + j.get_name() + j.get_status() + " [job] [path=" + t.get_cwd() + "]")
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
            if args.job:
                for j in t._jobs:
                    if j.get_name() not in args.job:
                        j._skip = True
        self.show_test()
        for t in self._tests:
            if not t._skip: 
                t._run()
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
        print("running test " + self.get_name())
        for j in self._jobs:
            if not j._skip: 
                j._run() 
        

class job(test_base):
    def __init__(self, job_name):
        super().__init__(job_name)
        self.file = file()
        self.env = env()
        self.cmd = cmd()
    def _run(self):
        print("running job " + self.get_name())
        cwd = self.get_cwd()
        sub.run('rm -rf ' + cwd, shell=True, check=True)
        sub.run('mkdir -p ' + cwd, shell=True, check=True)
        self.file._put(cwd)
        self.env._setup()
        self.cmd._run(cwd)
    def copy_from(self, j):
        self.file = copy.deepcopy(j.file)
        self.env = copy.deepcopy(j.env)
        self.cmd = copy.deepcopy(j.cmd)

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
            sub.run(sh_cmd + " " + os.path.abspath(f) + " .", shell=True, check=True, cwd=cwd)
            
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
            sub.run(s, shell=True, check=True, cwd=cwd)