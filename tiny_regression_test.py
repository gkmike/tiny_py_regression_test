import sys
import os
import argparse
import subprocess as sub
import copy
import threading

class test_base:
    def __init__(self, name: str):
        self._name = name
        self._skip = False
        self._parent = None
        self._event = threading.Event()
        self._wait_test = None
        self._status = "init"
        self._type = None
        self._sub_tests = []
    def get_cwd(self) -> str:
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()
    def get_name(self) -> str:
        return self._name
    def filter_sub_test(self, name_to_run, type_name):
        for t in self._sub_tests:
            if name_to_run not in t._name:
                if type_name == t._type:
                    t._event.set()
                    t._skip = True
                t.filter_test(name_to_run, type_name)
        return self
    def get_status(self) -> str:
        return self._status
    def after(self, test):
        self._wait_test = test
        return self
    def _add_sub_test(self, test):
        test._parent = self
        self._sub_tests.append(test)
    def _set_type(self, t: str):
        self._type = t
        return self
    def _show_test(self, indent=0):
        print(" " * indent, self.get_name(), "type=" + self._type, 
              "cwd="+self.get_cwd(), "status=" + self.get_status())
        for t in self._sub_tests:
            t._show_test(indent+4)
    def _run(self):
        raise NotImplementedError("class should impl run")
    def _wrap_run(self):
        if self._wait_test:
            print(self.get_name() + " waiting...")
            self._wait_test._event.wait()
        print("(running) " + self.get_name())
        if not self._skip: 
            self._run()
            print("(done) " + self.get_name())
        else:
            print("(skipped) " + self.get_name())
        self._event.set()
    def _parallel_run(self):
        threads = []
        for t in self._sub_tests:
            if not t._skip: 
                th = threading.Thread(target=t._wrap_run)
                threads.append(th)
                th.start()
        for th in threads:
            th.join()

class regression_test(test_base):
    def __init__(self, top_name):
        super().__init__(top_name)
        self._set_type("top")
    def create_test(self, name):
        t = test(name)._set_type("test")
        self._add_sub_test(t)
        return t
    def process(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', help='run all test')
        parser.add_argument('-t', '--test', nargs='*', help='run the specified test only')
        parser.add_argument('-j', '--job', nargs='*', help='run the specified job only')
        args = parser.parse_args()
        if len(sys.argv) == 1:
            print("=" * 80)
            self._show_test()
            print("=" * 80)
            parser.print_help()
            return
        if args.test:
            self.filter_sub_test(args.test, "test")
        if args.job:
            self.filter_sub_test(args.job, "job")
        self._parallel_run()
        self._show_test()
        #self._cwd_proc()
        #self._gen_pytest()
        #self._run_pytest()

class test(test_base):
    def __init__(self, test_name):
        super().__init__(test_name)
    def create_job(self, name):
        j = job(name)._set_type("job")
        self._add_sub_test(j)
        return j
    def _run(self):
        for j in self._sub_tests:
            if not j._skip: 
                j._wrap_run()
        

class job(test_base):
    def __init__(self, job_name):
        super().__init__(job_name)
        self.file = file()
        self.env = env()
        self.cmd = cmd()
    def _run(self):
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