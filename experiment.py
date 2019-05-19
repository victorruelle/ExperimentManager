import inspect
import os
import sys
import time
import logging

from utils import timestamp, setup_logger, pprint_dict, get_options
from run import Run
from signature import Signature
from stdout_capturing import StreamToLogger
from saving import Saver, VersionsHandler

'''
ExperimentManager does not support concurrency! When initializing an ExperimentManager instance, a specific sub-directoy is built in a specified experiments directory. No other processes should change the structure of this experiments directory. 

Things to work on:
	- fix the stoud capturing flush method, was going crazy when I did manager.main_logger.info even though main logger had been renamed internally to logger
	- create a smarter metrics logging method. Using a class with time etc.
	- add tensorboard support
	- add_config : add support for specific values in prefix ? not just dictionaries. 
	- improve the efficiency of get_call_id, I could record the deepest stack level when capturing functions to avoid going throug the entire stack everytime. Also pass ids in nested function calls whenever possible to avoid unnecassary calls.
	- implement self.ghost, I've bypassed it sometimes for now
	- add a method to create a run so that you can do self.run with the same runner multiple times
	- Handle or prevent nested calls to ExperimentManager.run (the id found will be that of the parent caller as of now).
	- Always make sure to add the run_id when logging for : save, add_config, run, etc.
	- Fix the name of captured commands/functions. It still doesn't seem right.
	- Implement add_sources. Code from polyrely should work easily.
'''



class ExperimentManager(object):

	def __init__(self,name,experiments_dir = None, project_dir = None, verbose = True, resume = False, **kwargs):
		''' Create a manager for your experiment. It can manage your parameter configurations, saving and loading of all ressources, logging and monitoring of any metrics and keep a saved version of the source files all in the right place and with the right versionning. You can use it to run predefined tasks in encapsulated environment with shared and run-specific options.

		# Args
			- name : name for the experiment. Will be used for creating the save directory, if needed
			- experiments_dir : the optionnal parent dir in which you want the manager to save its runs. If not provided, nothing will be saved.
			- project_dir : the parent directory of the code that is used to run the experiments. This is mostly used to backup the source code for more reproductability. If not provided, will use the parent dir of the file that called this init.
		
		'''
		super().__init__()
		
		# Setting the name of the experiment
		self.name = name
		
		# Setting the experiment mode. Ghost => nothing will be written (no directories, saves etc.).
		self.ghost = False
		
		# Checking if we are creating an experiment from a specific configuration
		self._force = '_force' in kwargs and kwargs['_force']
		self._resumed = '_resumed' in kwargs and kwargs['_resumed']
		
		
		# Trying to find the directory containig the source code, if not provided
		if project_dir is None:
			project_dir = os.path.abspath(os.path.dirname(inspect.stack()[0].filename))
		self.project_dir = project_dir
		
		# Finding the experiments directory in which to create this specific experiment.
		if experiments_dir is None:
			experiments_dir = os.path.join(self.project_dir,'minisacred_experiments')
		self.experiments_dir = experiments_dir
		
		if not os.path.isdir(self.experiments_dir):
			os.makedirs(self.experiments_dir)
		
		# Creating this specific experiment's directory using the experiment name and hand-cooked versionning. This is not a very safe/stable method.
		if not self.ghost: 
			if not self._force:
				experiment_name = '{} {}'.format(self.name,timestamp())
				experiment_dir = os.path.join(experiments_dir,experiment_name)
				index = 0
				while os.path.isdir(experiment_dir):
					index += 1
					experiment_dir = os.path.join(experiments_dir,'{} ({})'.format(experiment_name,index))
				os.mkdir(experiment_dir)
				self.experiment_dir = experiment_dir
				self.experiment_name = '{} ({})'.format(experiment_name,index)
			else:
				experiment_name = kwargs['experiment_name']
				experiment_dir = kwargs['experiment_dir']
			
			# Creating subdirectories for saved files and saved metrics
			self.save_dir = os.path.join(self.experiment_dir,'saved_files')
			os.makedirs(self.save_dir,exist_ok=True)
			self.metrics_dir = os.path.join(self.experiment_dir,'saved_metrics')
			os.makedirs(self.metrics_dir,exist_ok=True)
			self.runs_dir = os.path.join(self.experiment_dir,'saved_runs')
			os.makedirs(self.runs_dir,exist_ok=True)
		
		
		# Setting up loggers
		logger_path = os.path.join(self.experiment_dir,'experiment_info.log') if not self.ghost else None
		self.logger = setup_logger('experiment',logger_path)
		debug_logger_path = os.path.join(self.experiment_dir,'minisacred_debug.log') if not self.ghost else None
		self.debugger = setup_logger('minisacred_debug',debug_logger_path, level = logging.DEBUG)
		
		## Redirecting stdout and stderr to an unformatted logger
		std_logger_path = os.path.join(self.experiment_dir,'std_capture.log') if not self.ghost else None
		self.std_logger = setup_logger('std',std_logger_path,format = False)

		self.stdout_orig = sys.stdout
		stdout_capture = StreamToLogger(self.std_logger,logging.INFO, std_orig = self.stdout_orig)
		sys.stdout = stdout_capture
		
		self.stderr_orig = sys.stderr
		stderr_capture = StreamToLogger(self.std_logger,logging.ERROR, std_orig = self.stderr_orig)
		sys.stderr = stderr_capture
		
		# Initializing empty variables
		
		if not self._resumed:
			
			self.saving_versions = VersionsHandler() # a VesionHandler to keep track of saved files. Supports concurrency.
		
			self.runs_versions = VersionsHandler() # a VesionHandler to keep track of run_ids. Supports concurrency.
		
		else :
			
			self.saving_versions = VersionsHandler.from_config(kwargs['saving_versions']) # a VesionHandler to keep track of saved files. Supports concurrency.
		
			self.runs_versions = VersionsHandler.from_config(kwargs['runs_versions']) # a VesionHandler to keep track of run_ids. Supports concurrency.
		
			
		self.saver = Saver(self.saving_versions, logger = self.logger) # Creating handler for saving files during experiment
		
		self.runs = {} # will contain the run instance, keys are run_ids. 
		
		self.captured_functions = [] # will hold the list of functions in which experiment parameters are injected
		
		self.commands = {} # will hold the list of functions that can be called with experiment_manager_instance.run, keys are command names
		
		self.metrics = { "shared" : {} } # will contain MetricsLogers for each run as well as one that is global ('shared') 
		
		
		if not self._resumed:
			
			self.config = { "shared" : {} } # will contain Configuration dictionnaries for each run as well as one that is global ('shared')
		
			self.experiment_info = None # NOT IMPLEMENTED. Optionnal way of manually addin information to an experiment.
		
			self.host_info = None # NOT IMPLEMENTED. Should contain information about the host.
		
			self.beat_interval = 10.0  # (sec). NOT IMPLEMENTED.
			
		else : 
		
			self.config = kwargs['config']
		
		self.verbose = verbose # Verbosity level for the experiment internals. 
		
		
		# logging the end of the setup
		self.info('Finished setting up Experiment! Configuration is {}'.format(pprint_dict(self.get_config(),output='return',name='')))
		
		
	def info(self,message):
		if self.verbose:
			self.logger.info(message)
	
	def debug(self,message):
		if self.verbose:
			self.debugger.info(message)
	
	def debug_locals(self,locals_dict, limit = 2):
		if self.verbose:
			cout = pprint_dict(locals_dict,limit=limit,output='return', name = '')
			self.debug('{} - arguments on call \n{}'.format(inspect.stack()[1][3],cout))
		
	def add_config(self,config,run_id = None):
		self.debug_locals(locals())
		
		if run_id is None:
			run_id = ExperimentManager.get_call_id(logger=self.debugger)
		id = run_id if run_id is not None else 'shared'
		if self.verbose : 
			config_orig = self.config.copy()
		self.config[id].update(config)
		if self.verbose:
			self.info("Updated config for run_id {} \n{} \n{}".format(run_id,pprint_dict(config_orig,output = 'return', name = 'Before'),pprint_dict(self.config,output = 'return', name = 'After')))
		
	
	def capture(self,function, prefixes = None):
		''' Decorator to inject config parameters as default values in the a function.
		
		The injection will happen as follows :
			- we look for the run_id and add it to the injected parameters if found as _run_id, we also inject the run as _run, the run_path as _experiment_dir and the run_logger as _logger. We load the run-specific parameters.
			- if no run_id is foud, it means that the captured function was called outside of a ex.run. We will only inject the shared parameters.
			
		'''
		#self.debug_locals(locals())
		
		if function in self.captured_functions:
			return function
			# Nothing needs to be done
				
		# Capturing the signature
		sig = Signature(function)
		
		# Defining the captured function : we inject parameters
		def captured_function(*args,**kwargs):
			run_id = ExperimentManager.get_call_id(logger=self.debugger)
			options = get_options(self.config['shared'], run_dict = None if run_id is None else self.config[run_id], prefixes = prefixes)
			args, kwargs = sig.construct_arguments(args, kwargs, options,False)
			result = function(*args, **kwargs)
			return result
		
		# Recoverng the original name
		captured_function.__name__ = function.__name__
		
		# Adding to the list of captured functions
		self.captured_functions.append(captured_function)
		
		# Logging the result
		self.info('Captured function {} with prefixes {}'.format(function.__name__,prefixes))
		
		return captured_function		


	def command(self,function, prefixes = None):
		''' Decorator to add a function to list of callable commands. Also applies inject_config.			
		'''
		self.debug_locals(locals())
		
		# Checking that there is no other command by the same name. Better way to handle ? (maybe use an actual id instaed of function name)
		if function.__name__ in self.commands:
			raise Exception('a function going by the same name was already added : {}'.format(function.__name__))
			
		# Capturing the command function
		capture_function = self.capture(function,prefixes)
		
		# Adding to the list of commands
		self.commands.update({function.__name__ : capture_function})


	def log_scalar(self, metric_name, value, step, shared = False):
		"""
		Add a new measurement. If shared is set to true, the measurement will go to the shared metrics, otherwise it will be placed in the current run's metrics.
		"""
		self.debug_locals(locals())
		
		# Find the id of the desired metrics set
		if not shared:
			id = ExperimentManager.get_call_id(logger=self.debugger)
		if shared or id is None:
			id = 'shared'
		
		# Creating a new metrics logger if needed
		if metric_name not in self.metrics[id]:
			metrics_dir = self.metrics_dir if id=='shared' else self.runs[id].metrics_dir
			metric_path = os.path.join(metrics_dir,'{}.csv'.format(metric_name))
			self.metrics[id][metric_name] = setup_logger('{} {}'.format(id,metric_name),metric_path,format = False)
			
		# Adding a line to the log file
		self.metrics[id][metric_name].info('{};{}'.format(step,value))
		
		
	def save_sources(self, compress = True):
		''' Save a (compressed) copy of the source files in the experiment_dir for more reproductability
		'''
		self.debug_locals(locals())
		
		raise Exception('TO-DO')
		
		
	def run(self, command_name, update_dict = None, parallel = False, call_options = None):
		''' Run a capture command function in an encapsulated way. 
		
		This creates a run entry in the ExperimentManager with associated specific run parameters, experiment_dir, logs and run informations.		
		'''
		self.debug_locals(locals())
		self.info('Settig up environment for new run using command {} and update_dict {}'.format(command_name,update_dict))
		
		# Checking if the command exists
		if not command_name in self.commands:
			raise Exception('Command name {} is not recorded'.format(command_name))
	
		# Creating name and id for the run in a safe way.
		run_name, run_id = self.runs_versions.add('{} {}'.format(command_name,timestamp()), id = True)
		
		# Creating the associated directories and paths
		if not self.ghost :
		
			run_dir = os.path.join(self.runs_dir,run_name)
			run_logger_path = os.path.join(run_dir,'run.log')
			run_save_dir = os.path.join(run_dir,'saved_files')
			run_metrics_dir = os.path.join(run_dir,'saved_metrics')
			
			# will raise error if already exists
			os.makedirs(run_dir) 
			os.makedirs(run_save_dir)
			os.makedirs(run_metrics_dir)
			
		else:
			run_dir = None
			run_logger_path = None
			run_save_dir = None
			run_metrics_dir = None
			
		# Defining the logger 
		logger = setup_logger(run_name,run_logger_path)
		
		# Defining metrics
		self.metrics[run_id] = {}
		
		# Adding a config entry
		self.config.update({run_id:update_dict if update_dict is not None else {}})
		
		# Getting the actual command function
		command = self.commands[command_name]
		
		# Creating the Run instance
		run = Run(run_id,run_name,command,logger,run_dir,run_save_dir,run_metrics_dir)
		self.runs[run_id] = run
		
		# Logging the result
		self.info('Finished creating run, {}'.format(pprint_dict(run.__dict__,output='return',name='__dict__')))
		
		if call_options is None:
			call_options = {}
		
		# Actually doing the run
		self.logger.info('Startig run for command {} with id {}'.format(command, run_id))
		run(**call_options)
		self.logger.info('Finished run for command {} with id {} after {} seconds'.format(command, run_id,run.duration))
		
				
	
	def save(self,obj,name, method = None, shared = False, method_args = None, method_kwargs = None):
		''' Save an object without any thought! It will be added to the right folder (shared folder if no active run or if shared is enforced.
		
		The most general types are handled. If you want to setup customized saving methods, first use the add_saver method to define your custom saving method; you can then specify the method name here.
		
		Types that are handled : 
			- json serializable types
			- keras models
			- text like objects
			- list like objects (lists, arrays, numpy arrays, tensors...)
			- matplotlib figures
			
		Name can include the extension. If present, the Saver will look for methods with corresponding extensions (there is no handling of multiple matches as of now). 
		
		If no extension is given in the name and no method is specified, the Saver will try to figure out which method to use depending on the oject type.
		Look at the Saver class for more information.		
		'''
		
		self.debug_locals(locals())
		
		# Check if we must skip saving
		if self.ghost: 
			return
		
		# Finding the right save dir
		run_id = ExperimentManager.get_call_id(logger=self.debugger)
		save_dir = None
		if run_id is None or shared : 
			save_dir = self.save_dir
		else:
			save_dir = self.runs[run_id].save_dir
		
		if save_dir is None:
			return
			# this wil only happen if either the global save_dir or the run's experiment_dir has manually been set to None.
			# In that case, we assume that the user intended for nothing to be saved.
		
		# Calling the Saver objcet
		self.saver.save(obj,name,save_dir,method = method, method_args = method_args, method_kwargs = method_kwargs)
			
	
	def add_saver(self,method,name,extension):
		''' Add a custom saving method.
		
		The signature of the method should be : obj, path, *args, **kwargs.
		
		Name is the name of the saver to be used in the method parameter of ExperimentManager.save.
		
		Extension shoud be the expected file extension.
		'''
		self.debug_locals(locals())
		
		self.saver.add_saver(method,name,extension)		
		
	def close(self):
		''' Meant to clean up the experiment. Std redirections will be reset and all unsaved metrics and logs will be written.
		'''
		self.debug_locals(locals())
		
		self.logger.info('Closing off experiment. Std out and err are set back to original values. Unsaved metrics and logs will be saved.')
		sys.stdout = self.stdout_orig
		sys.stderr = self.stderr_orig
		
		
	'''
	Internal functions
	'''
		
	@staticmethod
	def get_call_id(target_filename = None, target_function = 'run', target_field = 'run_id', logger = None):
		''' Look through the stack trace for to retrieve a local value in a specific function of a specific file.
		'''
		
		stack = inspect.stack()

		if target_filename is None:
			target_filename = os.path.abspath(__file__)
		run_origin = None
		
		for i in range(len(stack)-1,-1,-1): # going backwards since the run call should be really early on
			frame = stack[i]
			function = frame.function
			filename = os.path.abspath(frame.filename)
			if filename == target_filename and function == target_function:
				run_origin = frame
				break
			else :
				pass
				
		if run_origin is None:
			return None
			raise Exception('No parent could be found, stack trace was {}'.format(stack))
		
		if not target_field in frame.frame.f_locals:
			raise Exception('{} was not found in parents\' locals'.format(target_field))
			
		if logger is not None:
			logger.info('get call id for {} found {}'.format(inspect.stack()[1][3],frame.frame.f_locals[target_field]))
		target_value = frame.frame.f_locals[target_field]

		return target_value
		
	def get_config(self):
		'''	Get the configuration dictionnary this experiment. 

		This can be used to recover the experiment with the from_config method.
		'''
		config = {
			"name" : self.name,
			"experiments_dir" : self.experiments_dir,
			"project_dir" : self.project_dir,
			"experiment_name" : self.experiment_name,
			"experiment_dir" : self.experiment_dir,
			"saving_versions" : self.saving_versions.get_config(),
			"runs_versions" : self.runs_versions.get_config(),
			"config" : { "shared" : self.config['shared'] } 
		}
		
		return config
		
		
	@staticmethod
	def from_config(config):
		''' Create or resume an experiment from a config file. 
		
		Read the assert_valid_config description for more information.
		'''
		
		ExperimentManager.assert_valid_config(config)
		
		return ExperimentManager(**config)
	
	@staticmethod
	def assert_valid_config(config):
		''' Check if a configuration dictionnary is valid.
		
		A configuration dict should contain at least the following fields:
			- name
			- experiments_dir
			- project_dir = None
			
		Having just these fields is enough the create a new Experiment. Optional fields are  
			- experiment_name OR experiment_dir : these two fields should be redundant! experiment_dir = os.path.join(experiments_dir,experiment_name). If both are given, the coherence between the two will be assessed. 
			
		If the provided experiment_name or experiment_dir point to an directory that already exist, the configuration will only be valid if it contains the following fields: 
			- saving_versions : the config dictionnary of the corresponding VersionsHandler
			- runs_versions : the config dictionnary of the corresponding VersionsHandler
			- config : the dictionnary containing a "shared" config dict. All others will be ignored.
		'''
		
		essentials = ['name','experiments_dir','project_dir']
		
		for param in essentials:
			assert param in config, 'Missing essential field {}'.format(param)
			
		experiment_name = None if 'experiment_name' not in config else config['experiment_name']
		experiment_dir = None if 'experiment_dir' not in config else config['experiment_dir']
		
		if not experiment_name and not experiment_dir:
			return
			# Ok for creating a new experiment
			
		if experiment_name and experiment_dir:
			assert experiment_dir == os.path.join(experiments_dir,experiment_name), 'Given experiment_name and experiment_dir are not coherent'
			
		if experiment_name and not experiment_dir:
			experiment_dir = os.path.join(experiments_dir,experiment_name)
			
		if not experiment_name and experiment_dir:
			experiment_name = os.path.basename(experiment_dir)
			
		assert '.' not in experiment_dir and '.' not in experiment_name
		
		if not os.path.isdir(experiment_dir):
			config.update({'_force': True})
			return
			# Ok for creating a new experiment with a specified name or dir
			
		# else, we need to check for the optionnals
		
		assert 'saving_versions' in config
		assert 'version' in config['saving_versions']
		assert 'runs_versions' in config
		assert 'version' in config['runs_versions']
		assert 'config' in config
		assert 'shared' in config['config']
		
		config.update({'_resumed': True})
		
		