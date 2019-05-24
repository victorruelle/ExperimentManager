__all__ = ['getManager']

import os
import inspect

from ExperimentManager.global_manager import global_manager
from ExperimentManager.experiment import ExperimentManager
from ExperimentManager.utils import pprint_dict


def getManager(name = None,experiments_dir = None, project_dir = None, verbose = True, resume = False, **kwargs):
    
    if name is None:
        name = get_call_id()

    if name in global_manager.experiments:
        return global_manager.experiments[name]

    else:
        caller_filename = os.path.abspath(inspect.stack()[1].filename)
        project_dir = project_dir if project_dir is not None else os.path.abspath(os.path.dirname(inspect.stack()[1].filename))
        manager = ExperimentManager(name,experiments_dir = experiments_dir, project_dir = project_dir, verbose = verbose, resume = resume, **kwargs)
        global_manager.add(manager,caller_filename)
        return manager


def get_call_id():
    ''' Look through the stack trace for to retrieve a local value in a specific function of a specific file.
    '''	
    
    stack = inspect.stack()

    for i in range(len(stack)-1,-1,-1): # going backwards since the run call should be really early on
        frame = stack[i]
        filename = os.path.abspath(frame.filename)
        if filename in global_manager.callers and 'manager' in frame.frame.f_locals:
            return frame.frame.f_locals['manager'].name
    
    raise Exception('Could not find an Experiment automatically')