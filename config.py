from pathlib import Path
import pwd
import grp

PARALLEL_TESTS = 2
PARALLEL_USERS = 1

BASE_DIR = Path('/judger').resolve()

RUN_USER_UID = pwd.getpwnam('code').pw_uid
RUN_GROUP_GID = grp.getgrnam('code').gr_gid

COMPILER_USER_UID = pwd.getpwnam('compiler').pw_uid
COMPILER_GROUP_GID = grp.getgrnam('compiler').gr_gid

SPJ_USER_UID = pwd.getpwnam('spj').pw_uid
SPJ_GROUP_GID = grp.getgrnam('spj').gr_gid

TEST_CASE_DIR = Path(__file__).resolve().parent / 'test-data'  # TODO: 改为相对django路径
# SPJ_SRC_DIR = '/judger/spj'
# SPJ_EXE_DIR = '/judger/spj'
