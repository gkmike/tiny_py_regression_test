from tiny_regression_test import regression_test

rt = regression_test("test_ws")
test = rt.create_test("code_test")
build_job = test.create_job("build_code")
build_job.file .links.append("example/src/*")
build_job.file.copys.append("example/pat/*")
build_job.env.append({"OPT": "-O2"})
build_job.cmd.steps.append("make")
build_job.cmd.result_checks.append("test a.out")

sim_job = test.create_job("run_program")
sim_job.file.links.append(build_job.get_cwd() + '/*')
sim_job.cmd.steps.append("./a.out > result.txt")
sim_job.cmd.result_checks.append("diff golden.txt result.txt")

rt.process()
