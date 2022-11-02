import base64
import hashlib
import os
import shutil
from multiprocessing import Pool
from pathlib import Path

import _judger

from compiler import Compiler
from config import BASE_DIR, PARALLEL_TESTS, TEST_CASE_DIR
from exceptions import JudgeServiceError
from languages import CONFIG, JudgeResult
from runner import Runner


class MakeJudgeDir(object):

    def __init__(self, task_id, debug=False):
        self.work_dir = BASE_DIR / task_id
        self.debug = debug

    def __enter__(self):
        try:
            self.work_dir.mkdir()
            os.chmod(self.work_dir, 0o711)
        except Exception:
            raise JudgeServiceError('failed to init runtime dir')
        return self.work_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.debug:
            return
        try:
            shutil.rmtree(self.work_dir)
        except Exception:
            raise JudgeServiceError('Failed to clean runtime dir')


def _run(instance, *args, **kwargs):
    return instance.judge_single(*args, **kwargs)


class Judger(object):
    """
        Case Config:
        [
            { id: 'XXXX', name: 'file name', score: 5 }
        ]
    """

    def __init__(self, task_id, case_id, test_case_config, subcheck_config,
                 result_queue):
        self.task_id = task_id
        self.test_case = TEST_CASE_DIR / case_id
        if not self.test_case.exists():
            raise JudgeServiceError('Test data not found!')
        self.test_case_config = test_case_config
        self.subcheck_config = subcheck_config
        self.pool = Pool(processes=PARALLEL_TESTS)
        self.result_queue = result_queue

    def judge(self, source_code, lang, limit_config):
        config = CONFIG.get(lang)
        if config is None:
            raise JudgeServiceError('Language not supported!')
        compile_config = config['compile']
        with MakeJudgeDir(self.task_id, debug=True) as working_dir:
            Path(working_dir / compile_config['src_name']) \
                .write_text(source_code, encoding='utf-8')
            compile_result, compile_log = Compiler.compile(
                working_dir, config['compile'])
            if compile_result['result'] != _judger.RESULT_SUCCESS \
                    and not Path(working_dir / compile_config['exe_name']).exists():
                # TODO: Find out why flag 3 is returned.
                self.result_queue.put(
                    self.make_report(
                        status=JudgeResult.COMPILE_ERROR,
                        score=0,
                        max_time=compile_result['real_time'],
                        max_memory=compile_result['memory'],
                        log=compile_log,
                        detail=[],
                    ))
                return
            self.result_queue.put({
                'type': 'compile',
                'data': str(compile_log)
            })
            jobs = []
            for case in self.test_case_config:
                result = self.pool.apply_async(
                    _run,
                    (
                        self,
                        working_dir,
                        case['name'],
                        config,
                        limit_config,
                    ),
                    callback=self.real_time_status,
                )
                jobs.append((result, case['score'], case.get('subcheck')))
            self.pool.close()
            self.pool.join()
            error_status = []
            score = 0
            detail = []
            max_time = 0
            max_memory = 0
            use_subcheck = self.test_case_config[0].get('subcheck') is not None
            subchecks = {}
            for i, j in self.subcheck_config.items():
                subchecks[int(i)] = j['score']
            for job in jobs:
                result = job[0].get()
                subcheck = job[2]
                if result['status'] == JudgeResult.ACCEPTED:
                    if not use_subcheck:
                        score += job[1]
                else:
                    if use_subcheck:
                        subchecks[subcheck] = 0
                    error_status.append(result['status'])
                time = result['statistic']['cpu_time']
                memory = result['statistic']['memory']
                detail.append({
                    'case_name': result['test_case'],
                    'status': result['status'],
                    'statistics': {
                        'time': time,
                        'memory': memory,
                        'exit_code': result['statistic']['exit_code']
                    },
                })
                if use_subcheck:
                    detail[-1]['subcheck'] = subcheck
                max_time = max(max_time, time)
                max_memory = max(max_memory, memory)
            if len(error_status) == 0:
                status = JudgeResult.ACCEPTED
            else:
                status = max(error_status)
            print(subchecks)
            if use_subcheck:
                score = sum(i for i in subchecks.values())
            self.result_queue.put(
                self.make_report(
                    status=status,
                    score=score,
                    max_time=max_time,
                    max_memory=max_memory,
                    log=compile_log,
                    detail=detail,
                ))

    def judge_single(self, working_dir, case_name, config, limit_config):
        in_file = self.test_case / f'{case_name}.in'
        out_file = working_dir / f'{case_name}.out'
        if not in_file.exists():
            return {
                'test_case': case_name,
                'status': JudgeResult.SYSTEM_ERROR,
                'output': 'Test input not found!',
                'statistic': {
                    'cpu_time': 0,
                    'memory': 0,
                    'exit_code': 0
                }
            }
        shutil.copyfile(in_file, working_dir / f'{case_name}.in')
        run_result = Runner.run(working_dir, config['compile']['exe_name'],
                                f'{case_name}.in', f'{case_name}.out',
                                config['run'], limit_config)
        status = run_result.pop('result')
        if status == _judger.RESULT_SUCCESS:
            if not out_file.exists():
                return {
                    'test_case': case_name,
                    'status': JudgeResult.WRONG_ANSWER,
                    'output': '',
                    'statistic': run_result
                }
            status, result = self.compare_output(case_name, out_file)
            output = base64.b64encode(result.encode('utf-8'))
            return {
                'test_case': case_name,
                'status': status,
                'output': str(output, 'utf-8'),
                'statistic': run_result
            }
        if status in (_judger.RESULT_CPU_TIME_LIMIT_EXCEEDED,
                      _judger.RESULT_REAL_TIME_LIMIT_EXCEEDED):
            status = JudgeResult.TIME_LIMIT_EXCEEDED
            if status != _judger.RESULT_CPU_TIME_LIMIT_EXCEEDED:
                run_result['cpu_time'] = run_result['real_time']
        elif status == _judger.RESULT_MEMORY_LIMIT_EXCEEDED:
            status = JudgeResult.MEMORY_LIMIT_EXCEEDED
        elif status == _judger.RESULT_RUNTIME_ERROR:
            status = JudgeResult.RUNTIME_ERROR
        else:
            status = JudgeResult.SYSTEM_ERROR
        output = ''
        if out_file.exists():
            output = out_file.read_bytes()
        return {
            'test_case': case_name,
            'status': status,
            'output': str(base64.b64encode(output), 'utf-8'),
            'statistic': run_result
        }

    def compare_output(self, case_name, out_file: Path):
        content = out_file.read_bytes()
        cleaned_content = b'\n' \
            .join(map(
                bytes.rstrip,
                content.rstrip().splitlines()
            ))
        content_md5 = hashlib.md5(cleaned_content).hexdigest()
        ans_md5_file = self.test_case / f'{case_name}.md5'
        if not ans_md5_file.exists():
            return JudgeResult.SYSTEM_ERROR, 'Test answer hash not found!'
        ans_md5 = ans_md5_file.read_text(encoding='utf-8', errors='ERROR')
        if content_md5 == ans_md5:
            return JudgeResult.ACCEPTED, ''
        return JudgeResult.WRONG_ANSWER, content.decode(
            encoding='utf-8', errors='Failed to decode output!')

    @staticmethod
    def make_report(status, score, max_time, max_memory, log, detail):
        return {
            'type': 'final',
            'status': int(status),
            'score': int(score),
            'statistics': {
                'max_time': int(max_time),
                'max_memory': int(max_memory)
            },
            'log': str(log),
            'detail': list(detail)
        }

    def real_time_status(self, detail):
        self.result_queue.put({
            'type': 'part',
            'test_case': detail['test_case'],
            'output': detail['output'],
            'status': detail['status'],
        })

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict
