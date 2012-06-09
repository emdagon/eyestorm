
from time import time

from should_dsl import *

from pprint import pprint


class Output():

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    GRAY = '\033[90m'
    ENDC = '\033[0m'

    def __init__(self, name):
        self.header("Describing %s:" % name)

    def _note(self, note=None):
        return Output.GRAY + " (%s)" % note if note else ""

    def _print(self, out):
        print out + Output.ENDC

    def header(self, message):
        out = Output.HEADER + message
        self._print(out)

    def notice(self, message, note=None):
        out = Output.OKGREEN + message
        out += self._note(note)
        self._print(out)

    def warning(self, message, note=None):
        out = Output.WARNING + message
        out += self._note(note)
        self._print(out)

    def error(self, message, note=None, detail=None):
        out = Output.FAIL + message
        out += self._note(note)
        if detail:
            out += "\n" + (" " * 10)
            out += Output.FAIL + detail
        self._print(out)

    def end(self):
        self._print("\n")


class Spec():

    it_tests = []
    results = []

    def before_all(self):
        pass

    def before_each(self):
        pass

    def after_all(self):
        pass

    def after_each(self):
        pass


__temp_it_tests = []


def describe(description):
    global __temp_it_tests
    description.it_tests = __temp_it_tests
    __temp_it_tests = []

    output = Output(description.__name__)
    instance = description()
    instance.before_all()
    for method in description.it_tests:
        instance.before_each()
        summary, result, timing = method(instance)
        instance.after_each()
        if result is True:
            output.notice(summary, str(timing))
        else:
            output.error(summary, str(timing), result)
    instance.after_all()
    output.end()


def it(summary):

    def wrapper(method):
        global __temp_it_tests

        def it_test(self):
            timer = time()
            try:
                method(self)
                result = True
            except Exception as error:
                result = str(error)
                raise
            return (summary, result, time() - timer)
        __temp_it_tests.append(it_test)
    return wrapper
