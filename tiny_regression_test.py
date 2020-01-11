import sys
import os
import time
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
        self.tv.bind('<ButtonRelease-1>', self.tv_click)
        self.tv.heading('0',text='test_name')
        self.tv.heading('1',text='test_status')
        self.tv.heading('2',text='job_name')
        self.tv.heading('3',text='job_status')
        self.tv.pack(side='left', fill='both')
        self.tv.tag_configure('skipped', background='#cccccc')
        self.tv.tag_configure('passed', foreground='forest green')
        self.tv.tag_configure('failed', foreground='red')
        self.tv.tag_configure('running', background='yellow')
        self.tv.tag_configure('waiting', background='lightblue')
        vsb = ttk.Scrollbar(self.root, orient="vertical", command=self.tv.yview)
        vsb.pack(side='left', fill='y')
        self.tv.configure(yscrollcommand=vsb.set)
        self.text = tk.Text()
        self.text.pack(side='left', fill='both')
        
        self.log_path_map = {}
        def on_close():
            self.root.destroy()
            quit()
        self.root.protocol("WM_DELETE_WINDOW", on_close)

    def tv_click(self, e):
        self.text.delete(1.0, tk.END)
        sn = self.tv.selection()[0]
        if sn in self.log_path_map:
            f = self.log_path_map[sn]
            if os.path.isfile(f):
                self.text.insert(1.0, "tail " + f + "\n")
                self.text.insert(tk.END, "-----\n")
                proc = sub.Popen(['tail',f],stdout=sub.PIPE)
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.decode()
                    self.text.insert(tk.END, line)

    def add_row(self, text_list, log_path=None):
        self.row_ptr += 1
        sn = self.tv.insert('', 'end', value=text_list)
        if log_path:
            self.log_path_map[sn] = log_path
        return sn
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
        self._log_path = None
    def get_cwd(self) -> str:
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()
    def get_name(self) -> str:
        return self._name

    def update_status(self):
        self.update_last_status()
        self.update_parent_status()   
 
    def update_parent_status(self):
        if len(self._sub_tests) == 0:
            return
        for t in self._sub_tests:
            t.update_parent_status()
        passed = self.is_sub_tests_passed()
        if passed is None:
            self.set_gui_status("")
            self._status = ''
            return
        if passed:
            self.set_gui_status("passed")
            self._status = 'passed'
        else:
            self.set_gui_status("failed")
            self._status = 'failed'


    def update_last_status(self):
        for t in self._sub_tests:
            t.update_last_status()
        s = self.get_last_status()
        if s != "":
            self._status = s 
            self.set_gui_status(s)
            

    def get_last_status(self):
        f_pass = self.get_cwd() + "/STATUS=PASSED"
        f_fail = self.get_cwd() + "/STATUS=FAILED"
        if os.path.isfile(f_pass):
            self._status = "passed"
            self._ret_code = 0
        elif os.path.isfile(f_fail):
            self._status = "failed"
            self._ret_code = 1
        return self._status

    def filter_sub_test(self, name_to_run, type_name):
        for t in self._sub_tests:            
            if type_name == t._type or type_name == 'any':
                if name_to_run not in t._name:
                    t._event.set()
                    t._skip = True
                    l = t.get_last_status()
                    s = "skipped"
                    if l != "":
                        s += " (last " + l + ")"
                    t._status = s
                    t.set_gui_status(s, "skipped")
                    t.filter_sub_test(name_to_run, 'any')
            t.filter_sub_test(name_to_run, type_name)
        return self
    def set_gui_status(self, text, tag=None):
        global g_gui
        global gui_en
        if tag is None:
            tag = text
        if gui_en:
            if self._type == "test":
                col = '1'
            elif self._type == "job":
                col = '3'
            else:
                return
            g_gui.tv.set(self._gui_tv_row_id, col, text)
            g_gui.tv.item(self._gui_tv_row_id, tag=tag)
        else:
            cwd = self.get_cwd()
            cwd = ('...' + cwd[-40:]) if len(cwd) > 40 else cwd
            output = '[' + time.asctime() + '] ' + cwd + " => " + text
            print(" "*100, end='\r')
            print(output, end='\r')
            
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
    def _get_status_row(self, failed_only):
        rows = []
        status = self._status
        if self._type == "test":
            rows.append([self._name, status, '', '', ''])
        elif self._type == "job":
            rows.append(['', '', self._name, status, self._log_path])
        if failed_only:
            if all(s not in status for s in ['failed', 'error']):
                rows = []
        for t in self._sub_tests:
            row = t._get_status_row(failed_only)
            rows.extend(row)
        return rows
    def _show_test(self, failed_only):
        col = ['test_name', 'test_status', 'job_name', 'job_status', 'log']
        rows = self._get_status_row(failed_only)
        tab = [col]
        tab.extend(rows)
        printTable(tab, self._name)
    def is_sub_tests_passed(self):
        ret = None
        for t in self._sub_tests:
            if t._status != "":
                if t._ret_code != 0:
                    ret = False
                    return ret
                else:
                    ret = True
        return ret
    def _run(self):
        raise NotImplementedError("class should impl run")
    def _wrap_run(self):
        global g_gui
        global gui_en
        if self._wait_test:
            self.set_gui_status("wait dependency", "waiting")
            self._wait_test._event.wait()
            if self._wait_test._ret_code != 0:
                self.set_gui_status("dependency error", 'failed')
                self._status = "dependency error"
                self._event.set()
                return -1
        self.set_gui_status("running")
        self._ret_code = self._run()
        self.set_gui_status(self._status)
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
    def show_test(self, failed_only):
        self._show_test(failed_only)
    def process(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', help='run all test')
        parser.add_argument('-t', '--test', nargs='*', help='run the specified test only')
        parser.add_argument('-j', '--job', nargs='*', help='run the specified job only')
        parser.add_argument('-l', '--list', action='store_true', help='list test only (dry run)')
        parser.add_argument('-g', '--gui', action='store_true', help='enable gui')
        parser.add_argument('-f', '--failed', action='store_true', help='show failed test only')
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
                self.update_status()
                g_gui.run(None)
            else:
                g_gui.run(self._parallel_run)
        else:
            if args.list:
                self.update_status()
                self.show_test(args.failed)
                return
            self._parallel_run()
        self._wait_job_done()
        if self.is_sub_tests_passed():
            self._status = "passed"
        else:
            self._status = "failed"
        self.show_test(args.failed)
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
        j._log_path = j.get_cwd() + '/run.log'
        j._gui_tv_row_id = g_gui.add_row(["", "", j._name, ""], j._log_path)
        return j
    def _run(self):
        ret_code = 0
        for j in self._sub_tests:
            if not j._skip:
                if ret_code == 0: 
                    ret_code = j._wrap_run()
                else:
                    j._event.set()
        if ret_code == 0:
            self._status = "passed"
        else:
            self._status = "failed"
        self._ret_code = ret_code
        return ret_code
        

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
        if path is list:
            self._list.expand(path)
        else:
            self._list.append(path)
        return self
    def remove(self, f=None):
        if f is None:
            self._list.clear()
        else:
            if f in self._list:
                self._list.remove(f)
            else:
                print("valid file list:") 
                print(self._list)
                raise ValueError('"' + f + '" not in file list')
        return self
    def replace(self, f_from, f_to):
        if f_from in self._list:
            sn = self._list.index(f_from)
            self._list[sn] = f_to
        else:
            print("valid file list:") 
            print(self._list)
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
    def _setup(self):
        for k,v in self._env.items():
            os.environ[k] = v
        
class cmd():
    def __init__(self):
        self._steps = []
    def add(self, cmd):
        if cmd is list:
            self._steps.extend(cmd)
        else:    
            self._steps.append(cmd)
        return self
    def remove(self, cmd=None):
        if cmd is None:
            self._steps.clear()
        else:
            if cmd in self._steps:
                self._steps.remove(cmd)
            else:
                print("valid command list:") 
                print(self._steps)
                raise ValueError('"' + cmd + '" not in command list')
        return self
    def replace(self, cmd_from, cmd_to):
        if cmd_from in self._steps:
            sn = self._steps.index(cmd_from)
            self._steps[sn] = cmd_to
        else:
            print("valid command list:") 
            print(self._steps)
            raise ValueError('"' + cmd_from + '" not in command list')
        return self
    def _run(self, cwd):
        log_f = cwd + '/run.log'
        sub.run('rm -f run.log', shell=True, cwd=cwd)
        sub.run('rm -f STATUS\=*', shell=True, cwd=cwd)
        f = open(log_f, 'a')
        for s in self._steps:
            r = sub.run(s, shell=True, cwd=cwd, stdout=f, stderr=f)
            if r.returncode != 0:
                f.close()
                sub.run('touch STATUS=FAILED', shell=True, cwd=cwd)
                return r.returncode
        f.close()
        sub.run('touch STATUS=PASSED', shell=True, cwd=cwd)
        return 0

"""
printTable by poke
https://stackoverflow.com/questions/19125237/a-text-table-writer-printer-for-python
"""
def printTable (tbl, top_name):
    fh = open(top_name+ '_result.log', 'w')
    cols = [list(x) for x in zip(*tbl)]
    lengths = [max(map(len, map(str, col))) for col in cols]
    f = '|' + '|'.join(' {:>%d} ' % l for l in lengths) + '|'
    s = '+' + '+'.join('-' * (l+2) for l in lengths) + '+'
    print(" "*100, end='\r')
    print(s)
    fh.write(s + '\n')
    for row in tbl:
        r = f.format(*row)
        print(r)
        fh.write(r + '\n')
        print(s)
        fh.write(s + '\n')
