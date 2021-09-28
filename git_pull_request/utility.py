
import distutils.util
import glob
import itertools
import logging as LOG
import operator
import os
import re
import subprocess
import sys
import attr
import tempfile
from urllib import parse
from loguru import logger





def split_and_remove_empty_lines(s):
    return filter(operator.truth, s.split("\n"))
