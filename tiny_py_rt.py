import sys
import argparse

class regression_test:
    def __init__(self):
        self._test = []
    def create_test(self, test_name):
        t = test(test_name)
        self.add_test(t)
        return test(test_name)
    def add_test(self, t):
        self._test.append(t)
    def show_test(self):
        print("[test_name]")
        for i in self._test:
            print(i.test_name)
    def process(self):
        parser = argparse.ArgumentParser()
        #parser.add_argument('')
        parser.parse_args()
        if len(sys.argv) == 1:
            self.show_test()
        #self._cwd_proc()
        #self._gen_pytest()
        #self._run_pytest()

class test:
    def __init__(self, test_name):
        self.test_name = test_name
        pass
    def create_job(self, job_name):
        return job(job_name)

class job:
    def __init__(self, job_name):
        self.job_name = job_name
        self._dep_jobs = []
        self.files = lambda: None
        self.files.links = []
        self.files.copys = []
        self.env_vars = [[]]
        self.cmds = lambda: None
        self.cmds.steps = []
        self.cmds.result_checks = []
    def add_dependency(self, job):
        self._dep_jobs.append(job)
    def working_dir(self):
        pass


