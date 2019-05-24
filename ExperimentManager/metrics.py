import os
import sys
import threading
import traceback

import numpy as np

from ExperimentManager.utils import setup_logger


class MetricsManager():
	''' Class to manage the metrics loggers for a single run ( ie: a single saving folder)
	
	The managers ID should be that of the associated run.
	'''
	
	
	def __init__(self,id,save_dir):
	
		self.id = id
		
		self.save_dir = save_dir
		
		self.metrics = {}
		
		self.lock = threading.Lock()
		
		
	def add_metric(self,name,headers = None):
		
		
		if name in self.metrics:
			raise Exception("Tried to add an already existing metric '{}' to MetricsManager having id '{}'".format(name,self.id))
		
		try:		
			self.lock.acquire()
			self.metrics[name] = MetricsLogger(name,os.path.join(self.save_dir,'{}.csv'.format(name)),headers = headers)

		except Exception as err:
			traceback.print_tb(err.__traceback__)
			print('Error type {} : {}'.format(sys.exc_info()[0],sys.exc_info()[1]))
			raise Exception('')

		finally:		
			self.lock.release()
			
	def log_scalar(self,metric,values,step=None, headers = None):
	
		if metric not in self.metrics:
			self.add_metric(metric, headers = headers)
			
		self.metrics[metric].log_scalar(values,step)


class MetricsLogger():
	
	def __init__(self, name, path, headers = None):
		
		# The name of the metric (should be secured before calling this logger => no duplicates!)
		self.name = name
		
		# The complete path to the log file (should be secured behore calling this logger)
		self.path = path
		
		# Duplicate logging to tensorboard, not yet implemented
		self.tensorboard = False 
		
		# The metrics logger
		self.logger = setup_logger(self.name,self.path, format = False)

		# Headers
		self.headers = headers
		if self.headers is not None:
			self.logger.info('step,'+','.join(self.headers))
		
		# History of last step for auto-incrementing
		self.last_scalar_step = -1
		self.last_scalar_lock = threading.Lock()
		
		
	def log_scalar(self,values,step=None):
		
		if step is None:
			try: 
				self.last_scalar_lock.acquire()
				self.last_scalar_step += 1
				step = self.last_scalar_step
			
			except Exception as err:
				traceback.print_tb(err.__traceback__)
				print('Error type {} : {}'.format(sys.exc_info()[0],sys.exc_info()[1]))
				raise Exception('')

			finally:
				self.last_scalar_lock.release()
		
		try:
			iter(values)
			self.logger.info('{},{}'.format(step,','.join( str(v) for v in values)))
		except:
			self.logger.info('{},{}'.format(step,values))
		
	
	def log_scalars(self,values,steps = None):
		''' Log multiple scalars at once using lists or numpy arrays.
		'''
		assert type(values) in (list,np.ndarray) and ( steps is None or type(steps) in (list,np.ndarray))
		
		if type(values) == np.ndarray:
			assert values.ndim == 1
		
		if type(steps) == np.ndarray:
			assert steps.ndim == 1
			
		if steps is None:
			steps = [ None ] * len(values)
		
		for x,y in zip(values,steps):
			self.log_scalar(x,y)
