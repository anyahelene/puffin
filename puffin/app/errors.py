class ErrorResponse(Exception):
    status = 'error'
    status_code = 400

    def __init__(self, message, *args, status_code=None, **kwargs) -> None:
        super().__init__(message, *args)
        self.data = kwargs
        if type(status_code) == int:
            self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            'status':self.status,
            'code':self.status_code,
            'message':self.args[0],
            'args':self.args[1:],
            **self.data
        }
        
