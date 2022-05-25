from multiprocessing import Pool
from pathlib import Path
import hashlib
import os
import shutil
import _judger

from compiler import Compiler
from runner import Runner
from languages import CONFIG, JudgeResult
from config import BASE_DIR, TEST_CASE_DIR, PARALLEL_TESTS
from exceptions import JudgeServiceError


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

    def __init__(self, task_id, case_id, case_conf, result_queue):
        self.task_id = task_id
        self.test_case = TEST_CASE_DIR / case_id
        if not self.test_case.exists():
            raise JudgeServiceError('Test data not found!')
        self.test_case_conf = case_conf
        self.pool = Pool(processes=PARALLEL_TESTS)
        self.result_queue = result_queue

    def judge(self, source_code, lang, limit_config):
        config = CONFIG.get(lang)
        if config is None:
            raise JudgeServiceError('Language not supported!')
        compile_config = config['compile']
        with MakeJudgeDir(self.task_id, debug=False) as working_dir:
            Path(working_dir / compile_config['src_name']).write_text(source_code, encoding='utf-8')
            compile_result, compile_log = Compiler.compile(working_dir, config['compile'])
            if compile_result['result'] != _judger.RESULT_SUCCESS:
                self.result_queue.put(self.make_report(
                    status=JudgeResult.COMPILE_ERROR,
                    score=0,
                    max_time=compile_result['real_time'],
                    max_memory=compile_result['memory'],
                    log=compile_log,
                    detail=[]
                ))
                return
            jobs = []
            for case in self.test_case_conf:
                result = self.pool.apply_async(_run, (
                    self,
                    working_dir,
                    case['name'],
                    config,
                    limit_config
                ))
                jobs.append((result, case['score']))
            self.pool.close()
            self.pool.join()
            error_status = []
            score = 0
            detail = []
            max_time = 0
            max_memory = 0
            for job in jobs:
                result = job[0].get()
                if result['status'] == JudgeResult.ACCEPTED:
                    score += job[1]
                else:
                    error_status.append(result['status'])
                time = result['statistic']['cpu_time']
                memory = result['statistic']['memory']
                detail.append({
                    'case_name': result['test_case'],
                    'status': result['status'],
                    'output': result['result'],
                    'statistics': {
                        'time': time,
                        'memory': memory,
                        'exit_code': result['statistic']['exit_code']
                    }
                })
                max_time = max(max_time, time)
                max_memory = max(max_memory, memory)
            status = JudgeResult.ACCEPTED if len(error_status) == 0 else max(error_status)
            self.result_queue.put(self.make_report(
                status=status,
                score=score,
                max_time=max_time,
                max_memory=max_memory,
                log=compile_log,
                detail=detail
            ))

    def judge_single(self, working_dir, case_name, config, limit_config):
        in_file = self.test_case / f'{case_name}.in'
        out_file = working_dir / f'{case_name}.out'
        if not in_file.exists():
            return JudgeResult.SYSTEM_ERROR, 'Test input not found!'
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
                    'result': '',
                    'statistic': run_result
                }
            status, result = self.compare_output(case_name, out_file)
            return {
                'test_case': case_name,
                'status': status,
                'result': result,
                'statistic': run_result
            }
        if status in (_judger.RESULT_CPU_TIME_LIMIT_EXCEEDED, _judger.RESULT_REAL_TIME_LIMIT_EXCEEDED):
            status = JudgeResult.TIME_LIMIT_EXCEEDED
            if status != _judger.RESULT_CPU_TIME_LIMIT_EXCEEDED:
                run_result['cpu_time'] = run_result['real_time']
        elif status == _judger.RESULT_MEMORY_LIMIT_EXCEEDED:
            status = JudgeResult.MEMORY_LIMIT_EXCEEDED
        elif status == _judger.RESULT_RUNTIME_ERROR:
            status = JudgeResult.RUNTIME_ERROR
        else:
            status = JudgeResult.SYSTEM_ERROR
        return {
            'test_case': case_name,
            'status': status,
            'result': '',
            'statistic': run_result
        }

    def compare_output(self, case_name, out_file: Path):
        content = out_file.read_bytes()
        cleaned_content = b'\n'.join(map(bytes.rstrip, content.rstrip().splitlines()))
        content_md5 = hashlib.md5(cleaned_content).hexdigest()
        ans_md5_file = self.test_case / f'{case_name}.md5'
        if not ans_md5_file.exists():
            return JudgeResult.SYSTEM_ERROR, 'Test answer hash not found!'
        ans_md5 = ans_md5_file.read_text(encoding='utf-8', errors='ERROR')
        if content_md5 == ans_md5:
            return JudgeResult.ACCEPTED, ''
        return JudgeResult.WRONG_ANSWER, content.decode(encoding='utf-8', errors='Failed to decode output!')

    @staticmethod
    def make_report(status, score, max_time, max_memory, log, detail):
        return {
            'status': int(status),
            'score': int(score),
            'statistics': {
                'max_time': int(max_time),
                'max_memory': int(max_memory)
            },
            'log': str(log),
            'detail': list(detail)
        }

    def __getstate__(self):
        self_dict = self.__dict__.copy()
        del self_dict['pool']
        return self_dict

#
# if __name__ == '__main__':
#     a = Judger('XX', 'abc-abc', [
#         {'id': 'test1', 'name': 'test1', 'score': 10},
#         {'id': 'test2', 'name': 'test2', 'score': 10},
#         {'id': 'test3', 'name': 'test3', 'score': 10},
#         {'id': 'test4', 'name': 'test4', 'score': 10},
#         {'id': 'test5', 'name': 'test5', 'score': 10},
#         {'id': 'test6', 'name': 'test6', 'score': 10},
#         {'id': 'test7', 'name': 'test7', 'score': 10},
#         {'id': 'test8', 'name': 'test8', 'score': 10},
#         {'id': 'test9', 'name': 'test9', 'score': 10},
#         {'id': 'test10', 'name': 'test10', 'score': 10}
#     ])
#     code = """
#     #include<stdio.h>
#     int main() {
#         int a, b;
#         scanf("%d %d", &a, &b);
#         printf("%d", a+b);
#         return 0;
#     }
#     """
#     limit = {"max_cpu_time": 2000, "max_memory": 128 * 1024 * 1024}
#     a.judge(code, 'c', limit)
