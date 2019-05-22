from ExperimentManager.experiment import ExperimentManager
from ExperimentManager.utils import pprint_dict

class GlobalManager():

    def __init__(self):
        self.experiment_manager = None

global_manager = GlobalManager()

def createManager(name,experiments_dir = None, project_dir = None, verbose = True, resume = False, **kwargs):
    
    # We can only have one experiment at a time!
    if global_manager.experiment_manager is not None:
        raise Exception('There is already an experiment running, {}'.format(pprint_dict(global_manager.experiment_manager.get_config(),output='return')))
    
    # Creating and recording the new ExperimentManager
    manager = ExperimentManager(name,experiments_dir = experiments_dir, project_dir = project_dir, verbose = verbose, resume = resume, **kwargs)
    global_manager.experiment_manager = manager
    return manager


def getManager():
    
    if global_manager.experiment_manager is None:
        raise Exception('There is not ExperimentManager instance running at the present time...')
    
    return global_manager.experiment_manager
