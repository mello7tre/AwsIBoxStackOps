from . import shared, fargs, istack
from .tools import concurrent_exec, get_exports
from .common import *

def update():
    stacks = istack.get_stacks()
    shared.exports = get_exports()
    print('update command:')
    pprint(stacks)
    result = concurrent_exec('update', stacks)
    print(result)

def parameters():
    stacks = istack.get_stacks()
    shared.exports = get_exports()
    print('parameters:')
    pprint(stacks)
    result = concurrent_exec('parameters', stacks)
    print(result)


