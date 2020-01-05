# tiny_py_regression_test
run regression test by the python description.
## Featrues
- Flow Control
  - multi-test paralle run with dependency supported
  - filter list to test supported
- Folders Generation
  - out-of-source build making your env clear
- GUI View Supported
  - check result easier

## Quick Start:
### example.py
```python
from tiny_regression_test import regression_test

rt = regression_test("test_ws")
test = rt.create_test("code_test")
build_job = test.create_job("build_code")
build_job.file.links.add("example/src/*")
build_job.file.copys.add("example/pat/*")
build_job.env.set("OPT", "-O2")
build_job.cmd.add("make")
build_job.cmd.add("test a.out")

sim_job = test.create_job("run_program")
sim_job.file.links.add(build_job.get_cwd() + '/*')
sim_job.cmd.add("make run | tee result.txt")
sim_job.cmd.add("diff golden.txt result.txt")
sim_job.env.set("STR", "123")

test2 = rt.create_test("code_test_no_opt")
build_job2 = test2.create_job("build_code").copy_from(build_job)
build_job2.env.set("OPT", "-O0")
sim_job2 = test2.create_job("run_program").copy_from(sim_job)
sim_job2.file.links.replace(build_job.get_cwd() + '/*', build_job2.get_cwd() + '/*')

test3 = rt.create_test("code_test_new_str")
sim_job3 = test3.create_job("run_program").copy_from(sim_job2).after(sim_job2)
sim_job3.env.set("STR", "456")
sim_job3.cmd.replace("diff golden.txt result.txt", "grep 456 result.txt")

sim_job3_error = test3.create_job("run_program_error").copy_from(sim_job3)
sim_job3_error.env.set("STR", "error")

rt.process()
```

### Run
``` sh
./example.py -a
```
#### result:
![image](https://github.com/gkmike/tiny_py_regression_test/blob/master/img/no_gui.png)


### Run with GUI
``` sh
./example.py -a -g
```
#### result
![image](https://github.com/gkmike/tiny_py_regression_test/blob/master/img/gui.png)



## Advanced Usage
### show total test
``` sh
./example.py -l
```

### run specific test
``` sh
./example.py -t new
```

### run specific job
``` sh
./example.py -j run
```


### enable gui
``` sh
./example.py {ARGS} -g
```
