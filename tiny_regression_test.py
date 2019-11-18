import sys
import os
import argparse
import subprocess as sub

class test_base:
    def __init__(self, name):
        self._name = name
        self._cwd = None
    def set_cwd(self, cwd):
        self._cwd = cwd
    def get_cwd(self):
        return self._cwd

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
        print("[test_name]")
        for i in self._tests:
            print(i._name)
    def process(self):
        parser = argparse.ArgumentParser()
        #parser.add_argument('')
        parser.parse_args()
        if len(sys.argv) == 1:
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
        j.set_cwd(self.get_cwd() + '/' + job_name)
        self._jobs.append(j)
        return j
    def run(self):
        for j in self._jobs:
            j.run()

class job(test_base):
    def __init__(self, job_name):
        super().__init__(job_name)
        self.file = file()
        self.env = env_vars()
        self.cmd = cmd()
    def run(self):
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
            sub.run("ln -sf", shell=True, check=True, cwd=cwd)
        for f in self.links:
            sub.run("cp -fr", shell=True, check=True, cwd=cwd)


class env_vars:
    def __init__(self):
        self._env = {}
    def append(self, env):
        self._env.update(env)
    def setup(self):
        for k,v in self._env:
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
            