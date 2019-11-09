class regression_test:
    def __init__(self):
        self._job = []
    def create_job(self, job_name):
        return job(job_name)
    def add_test(self, job):
        self._job.append(job)
    def process(self):
        pass


class job:
    def __init__(self, job_name):
        self._job_name = job_name
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


