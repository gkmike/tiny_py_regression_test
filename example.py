from tiny_py_rt import regression_test

rt = regression_test()
build_job = rt.create_job("build_code")
build_job.files.links.append("example/src/*")
build_job.files.copys.append("example/pat/*")
build_job.env_vars.append(["OPT", "-O2"])
build_job.cmds.steps.append("make")
build_job.cmds.result_checks.append("test a.out")
rt.add_test(build_job)

sim_job = rt.create_job("run program")
sim_job.add_dependency(build_job)
sim_job.files.links.append(build_job.working_dir())
sim_job.cmds.steps.append("./a.out > result.txt")
sim_job.cmds.result_checks.append("grep 'hello world' result.txt")
rt.add_test(sim_job)

rt.process()
