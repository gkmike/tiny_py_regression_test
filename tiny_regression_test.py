import sys
import os
import argparse
import subprocess as sub
import copy
import threading
import tkinter.ttk as ttk
import tkinter as tk

class test_gui:
    def __init__(self):
        self.root = tk.Tk()
        #self.root.geometry("500x500")
        self.row_ptr = 0
        self.col_ptr = 0
        self.tv = ttk.Treeview(self.root,columns=['0','1','2', '3'], show='headings')
        self.tv.heading('0',text='test_name')
        self.tv.heading('1',text='test_status')
        self.tv.heading('2',text='job_name')
        self.tv.heading('3',text='job_status')
        self.tv.pack(side='left', fill='both')
        self.tv.tag_configure('skipped', background='#cccccc')
        self.tv.tag_configure('passed', foreground='green')
        self.tv.tag_configure('failed', foreground='red')
        self.tv.tag_configure('running', background='yellow')
        self.tv.tag_configure('wait_dependency', background='lightblue')
        vsb = ttk.Scrollbar(self.root, orient="vertical", command=self.tv.yview)
        vsb.pack(side='right', fill='y')
        self.tv.configure(yscrollcommand=vsb.set)
        def on_close():
            self.root.destroy()
            quit()
        self.root.protocol("WM_DELETE_WINDOW", on_close)

    def add_row(self, text_list):
        self.row_ptr += 1
        return self.tv.insert('', 'end', value=text_list)
    def run(self, job_after):
        self.root.after(0, job_after)
        self.root.mainloop()
 
g_gui = test_gui()
gui_en = True

class test_base:
    def __init__(self, name: str):
        self._name = name
        self._skip = False
        self._parent = None
        self._event = threading.Event()
        self._wait_test = None
        self._status = ""
        self._type = None
        self._sub_tests = []
        self._job_threads = []
        self._gui_tv_row_id = None
        self._ret_code = -1
    def get_cwd(self) -> str:
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()
    def get_name(self) -> str:
        return self._name
    def filter_sub_test(self, name_to_run, type_name):
        for t in self._sub_tests:            
            if type_name == t._type or type_name == 'any':
                if name_to_run not in t._name:
                    t._event.set()
                    t._skip = True
                    t._status = "skipped"
                    t.set_gui_text("status", "skipped")
                    t.filter_sub_test(name_to_run, 'any')
            t.filter_sub_test(name_to_run, type_name)
        return self
    def set_gui_text(self, cell, text):
        global g_gui
        global gui_en
        if gui_en:
            if self._type == "test":
                col = '1'
            elif self._type == "job":
                col = '3'
            g_gui.tv.set(self._gui_tv_row_id, col, text)
            g_gui.tv.item(self._gui_tv_row_id, tag=text)
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
        print(" " * indent + self.get_cwd(), " [status=" + self.get_status() + "]")
        for t in self._sub_tests:
            t._show_test(indent+4)
    def is_sub_tests_passed(self):
        for t in self._sub_tests:
            if t._ret_code != 0:
                return False
            return t.is_sub_tests_passed()
        return True
    def _run(self):
        raise NotImplementedError("class should impl run")
    def _wrap_run(self):
        global g_gui
        global gui_en
        if self._wait_test:
            self.set_gui_text("status", "wait_dependency")
            self._wait_test._event.wait()
        self.set_gui_text("status", "running")
        self._ret_code = self._run()
        self.set_gui_text("status", "done")
        self.set_gui_text("status", self._status)
        self._event.set()
        return self._ret_code
    def _parallel_run(self):
        for t in self._sub_tests:
            if not t._skip: 
                th = threading.Thread(target=t._wrap_run)
                th.setDaemon(True)
                self._job_threads.append(th)
                th.start()
    def _wait_job_done(self):
        for th in self._job_threads:
            th.join()

class regression_test(test_base):
    def __init__(self, top_name):
        super().__init__(top_name)
        self._set_type("top")
    def create_test(self, name):
        t = test(name)._set_type("test")
        self._add_sub_test(t)
        global g_gui
        t._gui_tv_row_id = g_gui.add_row([t._name , "", "", ""])
        return t
    def show_test(self, indent=0):
        print("=" * 80)
        self._show_test(indent)
        print("=" * 80)        
    def process(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', help='run all test')
        parser.add_argument('-t', '--test', nargs='*', help='run the specified test only')
        parser.add_argument('-j', '--job', nargs='*', help='run the specified job only')
        parser.add_argument('-l', '--list', action='store_true', help='list test only (dry run)')
        parser.add_argument('-g', '--gui', action='store_true', help='enable gui')
        args = parser.parse_args()
        if len(sys.argv) == 1:
            parser.print_help()
            return
        if args.test:
            for t in args.test:
                self.filter_sub_test(t, "test")
        if args.job:
            for j in args.job:
                self.filter_sub_test(j, "job")
        if not args.gui:
            global gui_en
            gui_en = False
                       
        if args.gui:
            if len(sys.argv) == 2:
                parser.print_help()
                return
            global g_gui
            if args.list:
                g_gui.run(None)
            else:
                g_gui.run(self._parallel_run)
        else:
            self._parallel_run()
        if args.list:
            self.show_test()
            return
        self._wait_job_done()
        if self.is_sub_tests_passed():
            self._status = "passed"
        else:
            self._status = "failed"
        self.show_test()
        #self._show_test()
        #self._cwd_proc()
        #self._gen_pytest()
        #self._run_pytest()

class test(test_base):
    def __init__(self, test_name):
        super().__init__(test_name)
    def create_job(self, name):
        j = job(name)._set_type("job")
        self._add_sub_test(j)
        global g_gui
        j._gui_tv_row_id = g_gui.add_row(["", "", j._name, ""])
        return j
    def _run(self):
        for j in self._sub_tests:
            if not j._skip: 
                self._ret_code = j._wrap_run()
                if self._ret_code != 0:
                    self._status = "failed"
                    return self._ret_code
        self._status = "passed"
        return 0
        

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
        self._ret_code = self.cmd._run(cwd)
        if self._ret_code == 0:
            self._status = "passed"
        else:
            self._status = "failed (exit_code: " + str(self._ret_code) + ")"
        return self._ret_code
        
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
    def remove(self, f=None):
        if f is None:
            self._list.clear()
        else:
            if f in self._list:
                self._list.remove(f)
            else:
                raise ValueError('"' + f + '" not in file list')
        return self
    def replace(self, f_from, f_to):
        if f_from in self._list:
            sn = self._list.index(f_from)
            self._list[sn] = f_to
        else:
            raise ValueError('"' + f_from + '" not in file list')
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
    def remove(self, var=None):
        if var is None:
            self._env.clear()
        else:
            if var in self._env:
                del self._env[var]
            else:
                raise ValueError('"' + var + '" not in env list')
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
    def remove(self, cmd=None):
        if cmd is None:
            self._steps.clear()
        else:
            if cmd in self._steps:
                self._steps.remove(cmd)
            else:
                raise ValueError('"' + cmd + '" not in command list')
        return self
    def replace(self, cmd_from, cmd_to):
        if cmd_from in self._steps:
            sn = self._steps.index(cmd_from)
            self._steps[sn] = cmd_to
        else:
            raise ValueError('"' + cmd_from + '" not in command list')
        return self
    def _run(self, cwd):
        for s in self._steps:
            s = sub.run(s, shell=True, cwd=cwd)
            if s.returncode != 0:
                return s.returncode
        return 0
