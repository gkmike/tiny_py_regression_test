import sys
import os
import time
import argparse
import subprocess as sub
import copy
import threading
import tkinter.ttk as ttk
import tkinter as tk

failed_test_only = False

class test_gui:
    def __init__(self):
        self.root = tk.Tk()
        self.tv = ttk.Treeview(self.root, columns=['0', '1', '2', '3'], show='headings')
        self.tv.bind('<ButtonRelease-1>', self.tv_click)
        self.tv.heading('0', text='test_name')
        self.tv.heading('1', text='test_status')
        self.tv.heading('2', text='job_name')
        self.tv.heading('3', text='job_status')
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
                proc = sub.Popen(['tail', f], stdout=sub.PIPE)
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.decode()
                    self.text.insert(tk.END, line)

    def add_row(self, text_list, log_path=None):
        sn = self.tv.insert('', 'end', value=text_list)
        if log_path:
            self.log_path_map[sn] = log_path
        return sn

    def run(self, job_after):
        self.root.after(0, job_after)
        self.root.mainloop()

g_gui = test_gui()
gui_en = True


class table_handler:
    def __init__(self):
        self._gui_tv_row_id = None
        self._parent = None
        self._sub_tests = []
        self._status = ""
        self._is_passed = None
        self._type = None

    def add_sub_test(self, t):
        pass

    def add_sub_job(self, j):
        pass
    
    def set_status(self, text, tag=None):
        global g_gui
        global gui_en
        self._status = text
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
            if failed_test_only:
                if any(s in text for s in ['pass', 'skip']):
                    g_gui.tv.delete(self._gui_tv_row_id)
        else:
            cwd = self.get_cwd()
            cwd = ('...' + cwd[-40:]) if len(cwd) > 40 else cwd
            output = '[' + time.asctime() + '] ' + cwd + " => " + text
            print(" " * 100, end='\r')
            print(output, end='\r')

    def set_passed(self):
        self.set_status('passed')
        self._is_passed = True

    def set_failed(self):
        self.set_status('failed')
        self._is_passed = False

    def set_passed_value(self, is_passed):
        if is_passed == True:
            self.set_passed()
        elif is_passed == False:
            self.set_failed()
        else:
            self.set_status('')

    def get_cwd(self) -> str:
        if self._parent:
            return self._parent.get_cwd() + "/" + self.get_name()
        else:
            return self.get_name()

    def _get_status_row(self):
        global failed_test_only
        rows = []
        status = self._status
        if self._type == "test":
            rows.append([self._name, status, '', '', ''])
        elif self._type == "job":
            rows.append(['', '', self._name, status, self._log_path])
        if failed_test_only:
            if all(s not in status for s in ['failed', 'error']):
                rows = []
        for t in self._sub_tests:
            row = t._get_status_row()
            rows.extend(row)
        return rows

class test_base(table_handler):
    def __init__(self, name: str):
        super().__init__()
        self._name = name
        self._skip = False
        self._event = threading.Event()
        self._wait_test = None
        self._tests_in_thread = []
        self._log_path = None

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
        self.set_passed_value(passed)


    def update_last_status(self):
        for t in self._sub_tests:
            t.update_last_status()
        passed = self.is_last_passed()
        self.set_passed_value(passed)

    def is_last_passed(self):
        f_pass = self.get_cwd() + "/STATUS=PASSED"
        f_fail = self.get_cwd() + "/STATUS=FAILED"
        passed = None
        if os.path.isfile(f_pass):
            passed = True
        elif os.path.isfile(f_fail):
            passed = False
        return passed

    def filter_sub_test(self, name_to_run, type_name):
        for t in self._sub_tests:            
            if type_name == t._type or type_name == 'any':
                if name_to_run not in t._name:
                    t._event.set()
                    t._skip = True
                    passed = t.is_last_passed()
                    s = "skipped"
                    if passed:
                        s += " (last passed)"
                    else:
                        s += " (last failed)"
                    t.set_status(s, "skipped")
                    t.filter_sub_test(name_to_run, 'any')
            t.filter_sub_test(name_to_run, type_name)
        return self

    def after(self, test):
        self._wait_test = test
        return self

    def _add_sub_test(self, test):
        test._parent = self
        self._sub_tests.append(test)
        global g_gui
        test._gui_tv_row_id = g_gui.add_row([test._name, "", "", ""])

    def _add_sub_job(self, job):
        job._parent = self
        self._sub_tests.append(job)
        global g_gui
        job._log_path = job.get_cwd() + '/run.log'
        job._gui_tv_row_id = g_gui.add_row(["", "", job._name, ""], job._log_path)

    def _set_type(self, t: str):
        self._type = t
        return self

    def _show_test(self):
        col = ['test_name', 'test_status', 'job_name', 'job_status', 'log']
        rows = self._get_status_row()
        tab = [col]
        tab.extend(rows)
        printTable(tab, self._name)

    def is_sub_tests_passed(self):
        ret = None
        for t in self._sub_tests:
            if t._is_passed == False:
                ret = False
                return ret
            elif t._is_passed == True:
                ret = True
        return ret

    def _run(self):
        raise NotImplementedError("class should impl run")

    def _wrap_run(self):
        #global g_gui
        #global gui_en
        if self._wait_test:
            self.set_status("wait dependency", "waiting")
            self._wait_test._event.wait()
            if not self._wait_test._is_passed:
                self.set_status("dependency error", 'failed')
                self._event.set()
                return False
        self.set_status("running")
        passed = self._run()
        self.set_passed_value(passed)
        self._event.set()
        return passed

    def _parallel_run(self):
        for t in self._sub_tests:
            if not t._skip: 
                th = threading.Thread(target=t._wrap_run)
                th.setDaemon(True)
                self._tests_in_thread.append(th)
                th.start()

    def _wait_job_done(self):
        for th in self._tests_in_thread:
            th.join()


class regression_test(test_base):
    def __init__(self, top_name):
        super().__init__(top_name)
        self._set_type("top")

    def create_test(self, name):
        t = test(name)._set_type("test")
        self._add_sub_test(t)
        return t

    def show_test(self):
        self._show_test()

    def process(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', help='run all test')
        parser.add_argument('-t', '--test', nargs='*', help='run the specified test only')
        parser.add_argument('-j', '--job', nargs='*', help='run the specified job only')
        parser.add_argument('-l', '--list', action='store_true', help='list test only (dry run)')
        parser.add_argument('-g', '--gui', action='store_true', help='enable gui')
        parser.add_argument('-f', '--failed', action='store_true', help='show failed test only')
        args = parser.parse_args()
        global failed_test_only
        failed_test_only = args.failed
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
                self.show_test()
                return
            self._parallel_run()
        self._wait_job_done()
        if self.is_sub_tests_passed():
            self.set_passed()
        else:
            self.set_failed()
        self.show_test()


class test(test_base):
    def __init__(self, test_name):
        super().__init__(test_name)

    def create_job(self, name):
        j = job(name)._set_type("job")
        self._add_sub_job(j)
        return j

    def _run(self):
        passed = True
        for j in self._sub_tests:
            if not j._skip:
                if passed:
                    passed = j._wrap_run()
                else:
                    j._event.set()
        self.set_passed_value(passed)
        return passed
        

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
        passed = self.cmd._run(cwd, self.env._env)
        self.set_passed_value(passed)
        return passed
        
    def copy_from(self, j):
        self.file = copy.deepcopy(j.file)
        self.env = copy.deepcopy(j.env)
        self.cmd = copy.deepcopy(j.cmd)
        return self


class list_ext:
    def __init__(self):
        self._list = []

    def add(self, obj):
        ls = self._list
        if isinstance(obj, list):
            ls.extend(obj)
        else:
            ls.append(obj)
        return self

    def remove(self, obj=None):
        ls = self._list
        if obj is None:
            ls.clear()
        else:
            if obj in ls:
                obj.remove(o)
            else:
                print("valid list:")
                print(ls)
                raise ValueError('"' + obj + '" not in list')
        return self

    def replace(self, obj_from, obj_to):
        ls = self._list
        if obj_from in ls:
            sn = ls.index(obj_from)
            ls[sn] = obj_to
        else:
            print("valid list:")
            print(ls)
            raise ValueError('"' + obj_from + '" not in list')
        return self


class file:
    def __init__(self):
        self.links = file_handles()
        self.copys = file_handles()

    def _put(self, cwd):
        self.links._put("ln -sf", cwd)
        self.copys._put("cp -rf", cwd)


class file_handles(list_ext):
    def __init__(self):
        super().__init__()

    def _put(self, sh_cmd, cwd):
        for f in self._list:
            sub.run(sh_cmd + " " + os.path.abspath(f) + " .", shell=True, cwd=cwd)
            
class env:
    def __init__(self):
        self._env = {}

    def set(self, var, val):
        self._env[var] = str(val)
        return self

    def unset(self, var=None):
        if var is None:
            self._env.clear()
        else:
            del self._env[var]

class cmd(list_ext):
    def __init__(self):
        super().__init__()

    def _run(self, cwd, env_setting):
        log_f = cwd + '/run.log'
        sub.run('rm -f run.log', shell=True, cwd=cwd)
        sub.run(r'rm -f STATUS\=*', shell=True, cwd=cwd)
        f = open(log_f, 'a')
        f.write('------------------------\n* Env Settings:\n')
        for k,v in env_setting.items():
            f.write(k + '=' + v + '\n')
        f.write('------------------------\n* Commands Start:\n')
        f.flush()
        env_setting = {**os.environ, **env_setting}
        passed = True
        for s in self._list:
            r = sub.run(s, shell=True, cwd=cwd, stdout=f, stderr=f, env=env_setting)
            ret_code = r.returncode
            if ret_code != 0:
                passed = False
                f.write('------------------------\n* Error Command: ' + s)
                break
        f.close()
        if passed:
            sub.run('touch STATUS=PASSED', shell=True, cwd=cwd)
        else:
            sub.run('touch STATUS=FAILED', shell=True, cwd=cwd)
        return passed


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
