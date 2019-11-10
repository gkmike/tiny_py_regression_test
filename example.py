from tiny_py_rt import regression_test

rt = regression_test()
test = rt.create_test("code_test")
build_job = test.create_job("build_code")
build_job.files.links.append("example/src/*")
build_job.files.copys.append("example/pat/*")
build_job.env_vars.append(["OPT", "-O2"])
build_job.cmds.steps.append("make")
build_job.cmds.result_checks.append("test a.out")

sim_job = test.create_job("run_program")
sim_job.files.links.append(build_job.working_dir())
sim_job.cmds.steps.append("./a.out > result.txt")
sim_job.cmds.result_checks.append("diff golden.txt result.txt")

rt.process()
