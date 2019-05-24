import inspect
import os
import sys
import time
import logging
import shutil
from copy import deepcopy
import wrapt
import functools
import traceback

from ExperimentManager.utils import timestamp, setup_logger, pprint_dict, get_options
from ExperimentManager.run import Run
from ExperimentManager.signature import Signature
from ExperimentManager.stdout_capturing import StreamToLogger
from ExperimentManager.saving import Saver, VersionsHandler
from ExperimentManager.metrics import MetricsManager
from ExperimentManager.global_manager import global_manager

class ExperimentManager(object):

	def __init__(self,name,experiments_dir = None, project_dir = None, load_dir = None, verbose = True, resume = False, **kwargs):
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
		self.ghost = False if not 'ghost' in kwargs else kwargs['ghost']
		
		# Checking if we are creating an experiment from a specific configuration
		self._force = '_force' in kwargs and kwargs['_force']
		self._resumed = '_resumed' in kwargs and kwargs['_resumed']
		
		
		# Trying to find the directory containig the source code, if not provided
		if project_dir is None:
			project_dir = os.path.abspath(os.path.dirname(inspect.stack()[1].filename))
		self.project_dir = project_dir
		
		# Finding the experiments directory in which to create this specific experiment.
		if experiments_dir is None:
			experiments_dir = os.path.join(self.project_dir,'managed_experiments')
		elif not os.path.isabs():
			experiments_dir = os.path.join(self.project_dir,experiments_dir)
		self.experiments_dir = experiments_dir
		
		if not os.path.isdir(self.experiments_dir):
			os.makedirs(self.experiments_dir)

		if load_dir is not None:
			if not os.path.isabs(load_dir):
				load_dir = os.path.abspath(self.project_dir,load_dir)
		self.load_dir = load_dir

		
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
				self.experiment_name = kwargs['experiment_name']
				self.experiment_dir = kwargs['experiment_dir']
			
			# Creating subdirectories for saved files and saved metrics
			self.save_dir = os.path.join(self.experiment_dir,'saved_files')
			os.makedirs(self.save_dir,exist_ok=True)
			self.metrics_dir = os.path.join(self.experiment_dir,'saved_metrics')
			os.makedirs(self.metrics_dir,exist_ok=True)
			self.runs_dir = os.path.join(self.experiment_dir,'saved_runs')
			os.makedirs(self.runs_dir,exist_ok=True)
			self.sources_dir = os.path.join(self.experiment_dir,'saved_sources')
			os.makedirs(self.sources_dir,exist_ok=True)
			
		else:
			self.experiment_name = None
			self.experiment_dir = None
			self.save_dir = None
			self.metrics_dir = None
			self.runs_dir = None
			self.sources_dir = None
		
		
		# Setting up loggers
		logger_path = os.path.join(self.experiment_dir,'experiment_info.log') if not self.ghost else None
		self.logger = setup_logger('experiment',logger_path)
		debug_logger_path = os.path.join(self.experiment_dir,'minisacred_debug.log') if not self.ghost else None
		self.debugger = setup_logger('minisacred_debug',debug_logger_path, level = logging.DEBUG)
		
		## Redirecting stdout and stderr to an unformatted logger
		if not self.ghost:
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
		
		self.wrapped_functions = [] # will hold the list of functions in which experiment parameters are injected
		
		self.commands = {} # will hold the list of functions that can be called with experiment_manager_instance.run, keys are command names
		
		if not self.ghost:
			self.metrics = { -1 : MetricsManager(-1, self.metrics_dir) } # will contain MetricsLoggers for each run as well as one that is global (-1) 
		
		
		if not self._resumed:
			
			self.config = { -1 : {} } # will contain Configuration dictionnaries for each run as well as one that is global (-1)
		
			self.experiment_info = None # NOT IMPLEMENTED. Optionnal way of manually addin information to an experiment.
		
			self.host_info = None # NOT IMPLEMENTED. Should contain information about the host.
		
			self.beat_interval = 10.0  # (sec). NOT IMPLEMENTED.
			
		else : 
		
			self.config = kwargs['config']
		
		self.verbose = verbose # Verbosity level for the experiment internals. 

		self.task_queue = []
		
		# Saving the project sources
		if not self.ghost:
			self.save_project_sources()


		# Initializing metrics visualization processes

		
		
		# logging the end of the setup
		self.info('Finished setting up Experiment! Configuration is {}'.format(pprint_dict(self.get_config(),output='return',name='')))
		
	
	'''
	Messages
	'''
	
	def info(self,message):
		if self.verbose:
			self.logger.info(message)
	
	def debug(self,message):
		if self.verbose:
			self.debugger.info(message)
	
	def debug_locals(self, limit = 2):
		if self.verbose:
			stack = inspect.stack()
			locals_dict = stack[1].frame.f_locals
			cout = pprint_dict(locals_dict,limit=limit,output='return', name = '')
			self.debug('{} - arguments on call \n{}'.format(stack[1][3],cout))
	
	
	'''
	Configurations
	'''
		
		
	def add_config(self,config,run_id = None):
		self.debug_locals()
		
		if self.ghost:
			return
		
		if run_id is None:
			run_id = self.get_call_id()
		if self.verbose : 
			config_orig = deepcopy(self.config)
		self.config[run_id].update(config)
		if self.verbose:
			self.info("Updated config for run_id {} \n{} \n{}".format(run_id,pprint_dict(config_orig,output = 'return', name = 'Before'),pprint_dict(self.config,output = 'return', name = 'After')))
			
			
	def capture(self,wrapped=None, prefixes=None):
		''' Decorator to inject config parameters as default values in the a function.
		
		The injection will happen as follows :
			- we look for the run_id and add it to the injected parameters if found as _run_id, we also inject the run as _run, the run_path as _experiment_dir and the run_logger as _logger. We load the run-specific parameters.
			- if no run_id is foud, it means that the captured function was called outside of a ex.run. We will only inject the shared parameters.
			
		'''
		
		if wrapped is None:
			return functools.partial(self.capture,
					prefixes=prefixes)		
		
		if wrapped in self.wrapped_functions:
			return wrapped
			# Nothing needs to be done
				
		# Capturing the signature
		sig = Signature(wrapped)
		
		# Defining the wrapped function
		@wrapt.decorator
		def wrapped_function(wrapped, instance, args, kwargs):
			run_id = self.get_call_id()
			bound = (instance is not None)
			options = get_options(self.config[-1], run_dict = None if run_id is -1 else self.config[run_id], prefixes = prefixes)
			args, kwargs = sig.construct_arguments(args, kwargs, options,bound)
			result = wrapped(*args, **kwargs)
			return result
		
		# Recoverng the original name
		wrapped_function.__name__ = wrapped.__name__
		
		# Adding to the list of captured functions
		self.wrapped_functions.append(wrapped_function(wrapped,**{}))
		
		# Logging the result
		self.info('Captured function {} with prefixes {}'.format(wrapped.__name__,prefixes))
		
		return wrapped_function(wrapped,**{})
		
	'''
	Runs
	'''

	def queue_tasks(self,tasks):
		self.task_queue += tasks

	def run_queue(self):
		while len(self.task_queue)>0:
			task = self.task_queue.pop(0)
			try:
				self.run(task)
			except Exception as err:
				traceback.print_tb(err.__traceback__)
				self.logger.warn('Error type {} : {}'.format(sys.exc_info()[0],sys.exc_info()[1]))
	
	def command(self,wrapped=None, prefixes=None):
		''' Decorator to add a function to list of callable commands. Also applies inject_config.			
		'''
		
		if wrapped is None:
			return functools.partial(self.capture,
					prefixes=prefixes)		
		
		# Checking that there is no other command by the same name. Better way to handle ? (maybe use an actual id instaed of function name)
		if wrapped.__name__ in self.commands:
			raise Exception('a function going by the same name was already added : {}'.format(wrapped.__name__))
		
		if wrapped in self.wrapped_functions:
			return wrapped
			# Nothing needs to be done
				
		# Capturing the signature
		sig = Signature(wrapped)
		
		# Defining the wrapped function
		@wrapt.decorator
		def wrapped_function(wrapped, instance, args, kwargs):
			run_id = self.get_call_id()
			options = get_options(self.config[-1], run_dict = None if run_id is -1 else self.config[run_id], prefixes = prefixes)
			args, kwargs = sig.construct_arguments(args, kwargs, options,False)
			result = wrapped(*args, **kwargs)
			return result
		
		# Recoverng the original name
		wrapped_function.__name__ = wrapped.__name__
		
		# Adding to the list of captured functions
		self.wrapped_functions.append(wrapped_function(wrapped,**{}))
		
		# Adding to the list of commands
		self.commands.update({wrapped_function.__name__ : wrapped_function(wrapped,**{})})
		
		# Logging the result
		self.info('Captured function {} with prefixes {}'.format(wrapped.__name__,prefixes))
		
		return wrapped_function(wrapped,**{})
		
		
	def add_command(self,function):
		''' Add a function to the list of commands while bypassing the config capturing procedure.
		'''
		self.debug_locals()
		
		# Checking that there is no other command by the same name. Better way to handle ? (maybe use an actual id instaed of function name)
		if function.__name__ in self.commands:
			raise Exception('a function going by the same name was already added : {}'.format(function.__name__))
			
		# Adding to the list of commands
		self.commands.update({function.__name__ : function})
		

		
	def add_run(self, command_name, update_dict = None):
		''' Manually create a run for a command without running that command. This is handy when you want to run the same command multiple times with common logging and metrics. 

		Returns the created run. Make sure to recover at least that runs ID (run.id), this is needed to run it later on. 
		'''
	
		self.debug_locals()
		self.info('Settig up environment for new run using command {} and update_dict {}'.format(command_name,update_dict))
		
		# Checking if the command exists
		if not command_name in self.commands:
			raise Exception('Command name {} is not recorded'.format(command_name))
	
		# Creating name and id for the run in a safe way.
		run_name, run_id = self.runs_versions.add('{} {}'.format(command_name,timestamp()), return_id = True)
		
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
		if not self.ghost:
			self.metrics[run_id] = MetricsManager(run_id,run_metrics_dir)
		
		# Adding a config entry
		self.config[run_id] = {}
		if update_dict is not None:
			self.add_config(update_dict,run_id) # need to specify the run_id because, at this point, the run_id has not yet been declared in the run method
		
		# Getting the actual command function
		command = self.commands[command_name]
		
		# Creating the Run instance
		run = Run(run_id,run_name,command,logger,run_dir,run_save_dir,run_metrics_dir)
		self.runs[run_id] = run
		
		# Logging the result
		self.info('Finished creating run, {}'.format(pprint_dict(run.__dict__,output='return',name='__dict__')))
		
		return run
	
	def run_existing(self, run_id,  update_dict = None, parallel = False, call_options = None):
		''' Run an existing run instance using its ID. You could of course also directly call the run with you call_options, the advantage of using this method is that it will log the start and end of the run in the global log file.
		'''
		if not run_id in self.runs:
			raise Exception('run_id {} was not found in the saved runs : {}'.format(run_id,self.runs))
			
		run = self.runs[run_id]
	
		if call_options is None:
			call_options = {}
		
		# Actually doing the run
		self.logger.info('Startig run for command {} with id {} and configration {}'.format(run.command.__name__, run.id,pprint_dict(self.config,output='return')))
		call_id = run(**call_options)
		self.logger.info('Finished run for command {} with id {} after {} seconds'.format(run.command.__name__, run.id, run.calls_info[call_id]["duration"]))
	
	
	def run(self, command_name, update_dict = None, parallel = False, call_options = None):
		''' Run a capture command function in an encapsulated way. 
		
		This creates a run entry in the ExperimentManager with associated specific run parameters, experiment_dir, logs and run informations.		
		'''
		self.debug_locals()
		
		run = self.add_run(command_name, update_dict = update_dict)
		
		run_id = run.id
		
		if call_options is None:
			call_options = {}
		
		# Actually doing the run
		self.logger.info('Startig run for command {} with id {} and configration {}'.format(command_name, run.id,pprint_dict(self.config,output='return')))
		call_id = run(**call_options)
		self.logger.info('Finished run for command {} with id {} after {} seconds'.format(command_name, run.id, run.calls_info[call_id]["duration"]))
		
		
		
	'''
	Metrics
	'''
		

	def log_scalar(self, metric_name, values, step = None, run_id = None, headers = None):
		"""
		Add a new measurement. If shared is set to true, the measurement will go to the shared metrics, otherwise it will be placed in the current run's metrics.
		"""
		self.debug_locals()
		
		if self.ghost:
			return
		
		# Find the id of the desired metrics set
		if run_id is None:
			run_id = self.get_call_id()
		
		# Delegating to the right MetricsManager
		self.metrics[run_id].log_scalar(metric_name,values,step,headers = headers)
		
		
	'''
	Saving
	'''

	def get_save_path(self,path,*paths):
		''' Use the save dir to find absolute save path for files suing relative paths
		'''
		run_id = self.get_call_id()
		save_dir = self.save_dir if run_id == -1 else self.runs[run_id].save_dir
		if save_dir is None:
			return None
		return os.path.join(save_dir,path,*paths)
	
	def add_source(self,source):
		''' Add a file to the sources directory of this experiment. Sources are meant to be files that are required for the experiment to be run in the event that you would want to reproduce it.
		
		Source can be a relative path to the source file (relative to the project dir) or its absolute path but it must be contained in the project dir.
		'''
		
		if self.ghost:
			return
		
		load_path = os.path.abspath(source)
		
		if not os.path.isfile(load_path):
			self.logger.warn('Tried to load a source that does not exist at path {}'.format(load_path))
			return
			
		relative_source = os.path.relpath(source,self.project_dir)
		save_path = os.path.join(self.sources_dir,relative_source)
		save_dir = os.path.dirname(save_path)
		os.makedirs(save_dir,exist_ok=True)
		shutil.copy2(load_path,save_path)
		
		
	def save_project_sources(self, include_extensions = None, include_names = None, skip_dirs = None):
		''' Save a (compressed) copy of the source files in the experiment_dir for more reproductability
		'''
		
		if self.ghost:
			return
		
		include_extensions = ['py'] if include_extensions is None else include_extensions
		default_skip_dirs = ['__pycahce__','.git','managed_experiments']
		skip_dirs = default_skip_dirs if skip_dirs is None else skip_dirs+default_skip_dirs
		include_names = [] if include_names is None else include_names

		def assert_skip_dir(dirpath):
			dirpath = os.path.relpath(dirpath,self.project_dir)
			for skip_dir in skip_dirs:
				if skip_dir in dirpath:
					return True
			return False
		
		for dirpath,_, filenames in os.walk(self.project_dir):
			if assert_skip_dir(dirpath): 
				continue
			for filename in filenames:
				if filename.split('.')[-1] in include_extensions or os.path.basename(filename) in include_names:
					self.add_source(os.path.join(dirpath, filename))
	
	
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
		
		self.debug_locals()
		
		# Check if we must skip saving
		if self.ghost: 
			return
		
		# Finding the right save dir
		run_id = -1 if shared else self.get_call_id()
		save_dir = self.save_dir if run_id == -1 else self.runs[run_id].save_dir
		if save_dir is None:
			return
			# this wil only happen if either the global save_dir or the run's experiment_dir has manually been set to None.
			# In that case, we assume that the user intended for nothing to be saved.
		
		
		# Calling the Saver objcet
		return self.saver.save(obj,name,save_dir,method = method, method_args = method_args, method_kwargs = method_kwargs)
			
	
	def add_saver(self,method,name,extension):
		''' Add a custom saving method.
		
		The signature of the method should be : obj, path, *args, **kwargs.
		
		Name is the name of the saver to be used in the method parameter of ExperimentManager.save.
		
		Extension shoud be the expected file extension.
		'''
		self.debug_locals()
		
		if self.ghost:
			return
		
		self.saver.add_saver(method,name,extension)		
	
	"""
	Loading
	"""

	def get_load_path(self,path,*paths, **kwargs):
		''' Use the load dir to find absolute load path for files suing relative paths
		'''
		assert self.load_dir is not None,"Load dir is None, cannot use auto loading"
		return os.path.join(self.load_dir,path,*paths)


	'''
	Cleaning
	'''
	
	def close(self):
		''' Meant to clean up the experiment. Std redirections will be reset and all unsaved metrics and logs will be written.
		'''
		self.debug_locals()
		
		
		self.logger.info('Closing off experiment. Std out and err are set back to original values. Unsaved metrics and logs will be saved.')
		if not self.ghost:
			sys.stdout = self.stdout_orig
			sys.stderr = self.stderr_orig

		global_manager.remove(self.name)
		
		
	'''
	Support functions
	'''
		
	def get_call_id(self):
		''' Look through the stack trace for to retrieve a local value in a specific function of a specific file.
		'''	
		
		stack = inspect.stack()

		target_filename = os.path.abspath(__file__)
			
		run_id = -1
		
		for i in range(len(stack)-1,-1,-1): # going backwards since the run call should be really early on
			frame = stack[i]
			function = frame.function
			filename = os.path.abspath(frame.filename)
			if filename == target_filename and function in ['run','run_existing'] and 'run_id' in frame.frame.f_locals:
				run_id = frame.frame.f_locals['run_id']
				break
		
		self.logger.info('get call id for {} found {}'.format(inspect.stack()[1][3],run_id))
		return run_id
		
		
		
	

	'''
	MetricsManager saving/loading
	'''

	
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
			"config" : { -1 : self.config[-1] }, 
			"ghost" : self.ghost
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
			- config : the dictionnary containing a shared config dict (id=-1). All others will be ignored.
		'''
		
		essentials = ['name','experiments_dir','project_dir']
		
		for param in essentials:
			assert param in config, 'Missing essential field {}'.format(param)

		experiments_dir = config['experiments_dir']
			
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
		assert 'versions' in config['saving_versions']
		assert 'runs_versions' in config
		assert 'versions' in config['runs_versions']
		assert 'config' in config
		assert -1 in config['config']
		
		config.update({'_resumed': True})
		
		
