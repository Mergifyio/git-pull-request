
import operator
import os
from loguru import logger





def split_and_remove_empty_lines(s):
    return filter(operator.truth, s.split("\n"))



def check_not_none_and_logger(value, msg:str="", exit_code=os.EX_UNAVAILABLE, *error_values):
    check_and_logger(value, msg, exit_code, *[None, zero_value(value)])


def check_and_logger(value, msg:str="", exit_code=os.EX_UNAVAILABLE, *error_values):
    for checked in error_values:
        if checked == value:
            logger.critical(msg + "value:{value}")
            exit(exit_code)

def zero_value(value):
    if value != None:
        return type(value)()
    return None