import sys
import os
import argparse
import subprocess as sub

class test_base:
    def __init__(self, name):
        self._name = name
        self._cwd = None
        self._skip = False
    def set_cwd(self, cwd):
        self._cwd = cwd
    def get_cwd(self):
        return self._cwd
    def get_name(self):
        return self._name
    def status(self):
        if self._skip:
            return " (skipped)"
        return ""

class regression_test(test_base):
    def __init__(self, top_name):
        super().__init__(top_name)
        self._tests = []
        self.set_cwd(top_name)
    def create_test(self, test_name):
        t = test(test_name)
        t.set_cwd(self.get_cwd() + '/' + test_name)
        self._tests.append(t)
        return t
    def show_test(self):
        print("[test list]")
        for t in self._tests:
            print (t.get_name() + t.status())
            for j in t._jobs:
                print("  " + j.get_name() + j.status())
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
            t.run()
        #self._cwd_proc()
        #self._gen_pytest()
        #self._run_pytest()

class test(test_base):
    def __init__(self, test_name):
        super().__init__(test_name)
        self._jobs = []
    def create_job(self, job_name):
        j = job(job_name)
        j.set_cwd(self.get_cwd() + '/' + job_name)
        self._jobs.append(j)
        return j
    def run(self):
        print("running test " + self.get_name())
        for j in self._jobs:
            j.run()

class job(test_base):
    def __init__(self, job_name):
        super().__init__(job_name)
        self.file = file()
        self.env = env_vars()
        self.cmd = cmd()
    def run(self):
        print("running job " + self.get_name())
        cwd = self.get_cwd()
        sub.run('mkdir -p ' + cwd, shell=True, check=True)
        self.file.prepare(cwd)
        self.env.setup()
        self.cmd.execute(cwd)


class file:
    def __init__(self):
        self.links = []
        self.copys = []
    def prepare(self, cwd):
        for f in self.links:
            sub.run("ln -sf " + os.path.abspath(f) + " .", shell=True, check=True, cwd=cwd)
        for f in self.copys:
            sub.run("cp -rf " + os.path.abspath(f) + " .", shell=True, check=True, cwd=cwd)


class env_vars:
    def __init__(self):
        self._env = {}
    def append(self, env):
        self._env.update(env)
    def setup(self):
        for k,v in self._env.items():
            os.environ[k] = v
        
class cmd():
    def __init__(self):
        self.steps = []
        self.result_checks = []
    def execute(self, cwd):
        for s in self.steps:
            sub.run(s, shell=True, check=True, cwd=cwd)
        for s in self.result_checks:
            sub.run(s, shell=True, check=True, cwd=cwd)
            