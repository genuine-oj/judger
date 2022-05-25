import os
import shlex

import _judger

from config import RUN_USER_UID, RUN_GROUP_GID


class Runner(object):
    @staticmethod
    def run(working_path, exe_name, in_name, out_name, run_config, limit_config):
        command = run_config['command'].format(exe_path=working_path / exe_name)
        command = shlex.split(command)
        runner_in = working_path / in_name
        runner_out = working_path / out_name
        log_path = working_path / 'runner.log'
        os.chown(working_path, RUN_USER_UID, RUN_GROUP_GID)
        env = ['PATH=' + os.environ.get('PATH', '')] + run_config.get('env', [])
        seccomp_rule = run_config['seccomp_rule']
        run_result = _judger.run(max_cpu_time=limit_config['max_cpu_time'],
                                 max_real_time=limit_config['max_cpu_time'] * 3,
                                 max_memory=limit_config['max_memory'],
                                 max_stack=128 * 1024 * 1024,
                                 max_output_size=32 * 1024 * 1024,
                                 max_process_number=_judger.UNLIMITED,
                                 exe_path=command[0],
                                 input_path=str(runner_in),
                                 output_path=str(runner_out),
                                 error_path=str(runner_out),
                                 args=command[1::],
                                 env=env,
                                 log_path=str(log_path),
                                 seccomp_rule_name=seccomp_rule,
                                 uid=RUN_USER_UID,
                                 gid=RUN_GROUP_GID)
        return run_result
#
#
# if __name__ == '__main__':
#     from languages import cpp_lang_config
#
#     a = Runner()
#     limit = {"max_cpu_time": 2000, "max_memory": 5 * 1024 * 1024}
#     c = a.run(Path("/judger/test1"), "main", "test1.in", "test1.out", cpp_lang_config["run"], limit)
#     print(c)
