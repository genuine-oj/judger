import _judger
import json
from pathlib import Path
import os
import shlex

from config import COMPILER_USER_UID, COMPILER_GROUP_GID


class Compiler(object):
    @staticmethod
    def compile(working_path: Path, compile_config):
        command = compile_config.get('compile_command')
        if command is None:
            return 0, ''
        src_path = working_path / compile_config['src_name']
        exe_path = working_path / compile_config['exe_name']
        command = command.format(src_path=src_path, exe_path=exe_path)
        compiler_out = working_path / 'compiler.out'
        log_path = working_path / 'compiler.log'
        _command = shlex.split(command)
        os.chown(working_path, COMPILER_USER_UID, COMPILER_GROUP_GID)
        os.chdir(working_path)
        env = compile_config.get('env', [])
        env.append('PATH=' + os.getenv('PATH'))
        result = _judger.run(max_cpu_time=compile_config['max_cpu_time'],
                             max_real_time=compile_config['max_real_time'],
                             max_memory=compile_config['max_memory'],
                             max_stack=128 * 1024 * 1024,
                             max_output_size=20 * 1024 * 1024,
                             max_process_number=_judger.UNLIMITED,
                             exe_path=_command[0],
                             # /dev/null is best, but in some system, this will call ioctl system call
                             input_path=str(src_path),
                             output_path=str(compiler_out),
                             error_path=str(compiler_out),
                             args=_command[1::],
                             env=env,
                             log_path=str(log_path),
                             seccomp_rule_name=None,
                             uid=COMPILER_USER_UID,
                             gid=COMPILER_GROUP_GID)
        output = 'Compiler info: %s' % json.dumps(result)
        if compiler_out.exists():
            output = compiler_out.read_text(encoding='utf-8').strip()
            compiler_out.unlink(missing_ok=True)
        return result, output

#
# if __name__ == '__main__':
#     from languages import cpp_lang_config
#
#     a = Compiler.compile(Path('/judger/test1'), cpp_lang_config['compile'])
#     print(a)
