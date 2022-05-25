class JudgeServerException(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return f'Judge Error, info: {self.message}'


class SPJCompileError(JudgeServerException):
    pass


class JudgeServiceError(JudgeServerException):
    pass
