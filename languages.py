import enum

DEFAULT_ENV = ['LANG=en_US.UTF-8', 'LANGUAGE=en_US:en', 'LC_ALL=en_US.UTF-8']


class JudgeResult(enum.IntEnum):
    COMPILE_ERROR = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    TIME_LIMIT_EXCEEDED = 1
    MEMORY_LIMIT_EXCEEDED = 2
    RUNTIME_ERROR = 3
    SYSTEM_ERROR = 4


CONFIG = {
    'spj': {
        'compile': {
            'src_name':
            'checker.cpp',
            'exe_name':
            'checker',
            'max_cpu_time':
            10000,
            'max_real_time':
            20000,
            'max_memory':
            1024 * 1024 * 1024,
            'compile_command':
            '/usr/bin/g++ -DONLINE_JUDGE -O2 -W -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}',
        },
        'run': {
            'command':
            '{exe_path} {in_file_path} {user_out_file_path} {answer_file_path}',
            'seccomp_rule': 'general',  # Should use c_cpp
            'env': DEFAULT_ENV
        }
    },
    'c': {
        'compile': {
            'src_name':
            'main.c',
            'exe_name':
            'main',
            'max_cpu_time':
            3000,
            'max_real_time':
            5000,
            'max_memory':
            128 * 1024 * 1024,
            'compile_command':
            '/usr/bin/gcc -DONLINE_JUDGE -O2 -W -fmax-errors=3 -std=c99 {src_path} -lm -o {exe_path}',
        },
        'run': {
            'command': '{exe_path}',
            'seccomp_rule': 'general',  # Should use c_cpp
            'env': DEFAULT_ENV
        }
    },
    'cpp': {
        'compile': {
            'src_name':
            'main.cpp',
            'exe_name':
            'main',
            'max_cpu_time':
            3000,
            'max_real_time':
            5000,
            'max_memory':
            128 * 1024 * 1024,
            'compile_command':
            '/usr/bin/g++ -DONLINE_JUDGE -O2 -W -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}',
        },
        'run': {
            'command': '{exe_path}',
            'seccomp_rule': 'general',  # Should use c_cpp
            'env': DEFAULT_ENV
        }
    },
    'python3': {
        'compile': {
            'src_name':
            'solution.py',
            'exe_name':
            'solution.pyc',
            'max_cpu_time':
            3000,
            'max_real_time':
            5000,
            'max_memory':
            128 * 1024 * 1024,
            'compile_command':
            '/usr/bin/python3 -m compileall -l -f -b -q {src_path}',
        },
        'run': {
            'command': '/usr/bin/python3 {exe_path}',
            'seccomp_rule': 'general',
            'env': ['PYTHONIOENCODING=UTF-8'] + DEFAULT_ENV,
        },
    }
}
