#!/usr/bin/env python3
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
sim_job.cmd.add("./a.out > result.txt")
sim_job.cmd.add("diff golden.txt result.txt")

test2 = rt.create_test("code_test_no_opt")
build_job2 = test2.create_job("build_code").copy_from(build_job).after(sim_job)
build_job2.env.set("OPT", "-O0")
sim_job2 = test2.create_job("run_program").copy_from(sim_job)

rt.process()
