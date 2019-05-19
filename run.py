import time
import os
from utils import timestamp
import superjson
from utils import pprint_dict


class Run():
	''' A simple container class. Used to capture basic information about a run. 
	
	The actual run metrics and saving utilities are managed globally by an ExperimentManager.	
	'''

	def __init__(self,id,name,command,logger,run_dir, save_dir, metrics_dir):
	
		self.command = command
		"""The command that should be run"""
	
		self._id = id
		"""The ID of this run as assigned by the experiment Manager"""

		self.name = name
		
		self.run_dir = run_dir
		
		self.save_dir = save_dir
		
		self.metrics_dir = metrics_dir
		
		self.logger = logger
		"""The logger that is used for this run"""

		self.result = None
		"""The return value of the main function"""

		self.status = None
		"""The current status of the run, from QUEUED to COMPLETED"""

		self.start_time = None
		"""The datetime when this run was started"""

		self.stop_time = None
		"""The datetime when this run stopped"""
		
		self.duration = None
		
		
	def __call__(self,*args,**kwargs):
		self.status = 'Running'
		self.start_time = timestamp()
		_start_time = time.time()
		self.result = self.command(*args,**kwargs) # raises Error if no return ? 
		self.stop_time = timestamp()
		_stop_time = time.time()
		self.duration = round(_stop_time - _start_time,3)
		self.status = 'Finished'
		with open(os.path.join(self.run_dir,'run_info.log'),'w') as output:
			output.write(pprint_dict(self.get_config(),output='return',name='Run config'))
		
	def get_config(self):
		config = { key : getattr(self,key) for key in self.__dict__  if key not in ['logger','command']}
		config['logger'] = self.logger.name
		config['command'] = self.command.__name__
		return config