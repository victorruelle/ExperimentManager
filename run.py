import time
import os
from utils import timestamp
import superjson
from utils import pprint_dict
import threading


class Run():
	''' A simple container class. Used to capture basic information about a run. 
	
	The actual run metrics and saving utilities are managed globally by an ExperimentManager.	
	'''

	def __init__(self,run_id, name,command, logger, run_dir, save_dir, metrics_dir):
	
		self.command = command
		"""The command that should be run"""
	
		self.id = run_id
		"""The ID of this run as assigned by the experiment Manager"""

		self.name = name
		
		self.run_dir = run_dir
		
		self.save_dir = save_dir
		
		self.metrics_dir = metrics_dir
		
		self.logger = logger
		"""The logger that is used for this run"""

		self.results = {}
		"""The return value of the main function"""

		self.status = None
		"""The current status of the run, from QUEUED to COMPLETED"""

		self.calls_info = {}
		self.calls_lock = threading.Lock()
		
	def increment_calls(self):
		try:
			self.calls_lock.acquire()
			id = len(self.calls_info)
			self.calls_info[id] = {'start_time':None,'stop_time':None,'duration':None}
		finally:
			self.calls_lock.release()
		return id
		
		
	def __call__(self,*args,**kwargs):
		self.status = 'Running'
		call_id = self.increment_calls()
		self.calls_info[call_id]['start_time'] = timestamp()
		self.logger.info('({}) Starting call number {} with *args {} and **kwargs {}'.format(self.calls_info[call_id]['start_time'],call_id,args,kwargs))
		_start_time = time.time()
		self.results[call_id] = self.command(*args,**kwargs)
		_stop_time = time.time()
		self.calls_info[call_id]['stop_time'] = timestamp()
		self.logger.info('({}) Finished run.'.format(self.calls_info[call_id]['stop_time']))
		self.calls_info[call_id]['duration'] = round(_stop_time - _start_time,3)
		self.status = 'Finished'
		with open(os.path.join(self.run_dir,'run_info.log'),'w') as output:
			output.write(pprint_dict(self.get_config(),output='return',name='Run config'))
			
		return call_id
		
	def get_config(self):
		config = { key : getattr(self,key) for key in self.__dict__  if key not in ['logger','command']}
		config['logger'] = self.logger.name
		config['command'] = self.command.__name__
		return config