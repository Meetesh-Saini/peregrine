from codes import *

class ErrorHandler():
    suppress_warnings = False

    def log_error(self, msg):
        print(f"\033[31mError:\033[0m {msg}")

    def log_warning(self, msg):
        if not self.suppress_warnings:
            print(f"\033[31mWarning:\033[0m {msg}")

    def log(self, code):
        if code != SUCCESS:
            self.log_error(self.errors[code])

    errors = {
        NO_PEREGRINE_DIR : "Peregrine is not initialised in this directory. Use `init` to initialise it.",
        NO_INDEX : "index file not found in peregrine directory. Use `init` to create new one.",
        NO_PEREGRINEFILE : "peregrinefile file not found in peregrine directory. Use `init` to create new one.",
        INVALID_PATH : "No such path exists",
        OUT_OF_SCOPE_PATH : "Permission denied. The requested path is out of scope of peregrine.",
    }