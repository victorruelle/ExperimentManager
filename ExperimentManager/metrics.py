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
		
		
	def add_metric(self,name,header = None):
		
		
		if name in self.metrics:
			raise Exception("Tried to add an already existing metric '{}' to MetricsManager having id '{}'".format(name,self.id))
		
		try:		
			self.lock.acquire()
			self.metrics[name] = MetricsLogger(name,os.path.join(self.save_dir,'{}.csv'.format(name)),header = header, tensorboard = self.tensorboard)

		except Exception as err:
			traceback.print_tb(err.__traceback__)
			print('Error type {} : {}'.format(sys.exc_info()[0],sys.exc_info()[1]))
			raise Exception('')

		finally:		
			self.lock.release()
			
	def log_scalar(self,metric,value,step=None):
	
		if metric not in self.metrics:
			self.add_metric(metric, header = [metric])
			
		step = self.metrics[metric].log_scalar(value,step)
		
		return step
		
	def log_scalars(self,metric,values,header, step=None):
	
		if metric not in self.metrics:
			self.add_metric(metric, header = header)
			
		step = self.metrics[metric].log_scalars(values,step)
		return step


class MetricsLogger():
	
	def __init__(self, name, path, header = None):
		
		# The name of the metric (should be secured before calling this logger => no duplicates!)
		self.name = name
		
		# The complete path to the log file (should be secured behore calling this logger)
		self.path = path
		
		# The metrics logger
		self.logger = setup_logger(self.name,self.path, format = False)

		# Headers, should be a list!
		self.header = header
		if self.header is not None:
			self.logger.info('step,'+','.join(self.header))
		
		# History of last step for auto-incrementing
		self.last_scalar_step = -1
		self.last_scalar_lock = threading.Lock()
		
		# To check the coherence between calls
		self.n_vals = len(self.header)
		
	def verify_call(self,n_inputs):
		assert self.n_vals = n_inputs
		
	
	def get_step(self,step=None):
		if step is None:
			try: 
				self.last_scalar_lock.acquire()
				self.last_scalar_step += 1
				return self.last_scalar_step
			
			except Exception as err:
				traceback.print_tb(err.__traceback__)
				print('Error type {} : {}'.format(sys.exc_info()[0],sys.exc_info()[1]))
				raise Exception('')

			finally:
				self.last_scalar_lock.release()
		return step
		
		
	def log_scalar(self,value,step=None):
		self.verify_call(1)
		step = self.get_step(step)
		self.logger.info('{},{}'.format(step,value))
		return step
			
	def log_scalars(self,values,step=None):	
		self.verify_call(len(values))
		step = self.get_step(step)
		self.logger.info('{},{}'.format(step,','.join( str(v) for v in values)))
		return step
	
