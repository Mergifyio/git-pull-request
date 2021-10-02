
import operator
import os
from loguru import logger


def split_and_remove_empty_lines(s):
    return filter(operator.truth, s.split("\n"))

def check_true_value_and_logger(value, msg:str="", exit_code=None, *error_values):
    check_and_logger(value, msg, exit_code, *[None, zero_value(value)])

def check_and_logger(value, msg:str="", exit_code=None, *error_values):
    for checked in error_values:
        if checked == value:
            logger.critical(msg + "value:{value}")
            if exit_code: 
                dead_for_resource()
            else:
                return

def zero_value(value):
    if value != None:
        return type(value)()
    return None

def dead_for_resource():
    exit(os.EX_UNAVAILABLE)

def dead_for_software():
    exit(os.EX_SOFTWARE)
