import threading 
import os
from keras.models import Model as keras_Model, save_model
from superjson import json
from numpy import ndarray, save as np_save
from tensorflow import Tensor
from keras.backend import eval
from matplotlib.pyplot import Figure as plt_Figure
import inspect
import logging


class Saver():
	''' A class to thoughtlessly save any object.
	
	Implements generic saving methods and easily allows for custom methods to be added.	
	'''

	def __init__(self,verions_handler = None, logger = None):
		
		self.verions_handler = verions_handler if verions_handler is not None else VersionsHandler()
		
		self.savers = {}
		
		# Adding useful savers
		self.savers['matplotlib'] = Method(save_plt,'fig','png')
		self.savers['json'] = Method(save_json,'json','json')
		self.savers['numpy'] = Method(save_numpy,'numpy','npy')
		self.savers['string'] = Method(save_str,'string','txt')
		self.savers['keras'] = Method(save_keras,'keras','h5')
		
		self.logger = logger if logger is not None else logging.getLogger('ExperimentSaver')
		self.logger.setLevel(logging.INFO)
		
	def get_path(self,name,extension,dir):
		''' Get a safe saving path.
		'''
		save_name = '{}.{}'.format(name,extension)
		save_path = self.verions_handler.add(os.path.join(dir,save_name))
		return save_path
	
	
	def save(self,obj,name,save_dir,method = None, method_args = None, method_kwargs = None):
		''' Save an object given a name and a directory in which to save. 
		
		The optional method parameter should be a string corresponding to the name of an existing method in self.savers. 		
		'''
		if method is not None:
			assert method in self.savers, 'No saver found for {}'.format(locals())
	
		# Check if the extension was manually specified, try to comply if so
		elif '.' in name:
			split_name = name.split(".")
			if len(split_name) != 2:
				raise Exception('Found abnormal name in Saver.save : {}'.format(name))
			name,extension = split_name
			
			# Find a method matching the extension
			for internal_method in self.savers.values():
				if internal_method.extension == extension:
					method = internal_method.name
					break
			if method is None:
				self.logger.warn('Could not find a method atching the specified extension {} when saving {}. Now trying to find a suitable saving method.'.format(extension,name))
		
		# Finding the right saving method (could be called even if an extension was given (but no method was found)
		if method is None:			
			'''
			Converting types
			'''
			if isinstance(obj,Tensor):
				try:
					obj = eval(obj)
				except:
					self.logger.warn('in Saver, Tensor could not be evaluated, string representation will be used instead...')
					obj = str(obj)				
			
			'''
			Finding a method
			'''

			if isinstance(obj,plt_Figure):
				method = 'matplotlib'
		
			if isinstance(obj,keras_Model):
				method = 'keras'
				
			if isinstance(obj,str):
				method = 'string'
			
			elif isinstance(obj,list) or isinstance(obj,ndarray):
				method = 'numpy'
				
			elif isinstance(obj,dict):
				method = 'json'
			
			else:
				try:
					_ = json.dumps(obj)
					method = 'json'
				except:
					self.logger.warn('Could not save to last resort json dump for {}'.format(name))
					return
					# we exit, seeing as no method could be found
					
		
		assert method is not None, 'Internal implementation error'
			
		# Getting the actual method
		method = self.savers[method]
			
		# Setting the method args
		if method_args is None:
			method_args = []
		if method_kwargs is None:
			method_kwargs = {}
			
		# Getting the correct save_path in a safe way
		save_path = self.get_path(name,method.extension,save_dir)
		
		# Saving
		method(obj,save_path,*method_args,**method_kwargs)
		
		# Logging the result
		self.logger.info('Saver saved {}'.format(save_path))
				
			
			
	def add_saver(self,method,name,extension):
		''' The method should be wrapped to work with two params at least : obj, path. *args and **kwargs can be added.
		'''
		self.savers[name] = Method(method,name,extension)
		
		
class Method(object):

	def __init__(self,method,name,extension):	
		super().__init__()
		self.name = name
		self.method = method
		self.extension = extension
		
	def __call__(self,*args,**kwargs):
		self.method(*args,**kwargs)
		
		

class VersionsHandler(object):

	def __init__(self):
		super().__init__()
		self.versions = {}
		self.lock = threading.Lock()
		
	def add(self,name, return_id = False):
		try :
			self.lock.acquire()
			if name in self.versions:
				self.versions[name] += 1
				name += ' ({})'.format(self.versions[name])
			else:
				self.versions[name] = 0
			if return_id:
				output = (name,len(self))
			else:
				output = name
		except:
			raise Exception(inspect.stack())
		finally:
			self.lock.release()
		return output
		
	def __getitem__(self,key):
		return self.versions[key]
		
	def __len__(self):
		return sum([value + 1 for value in self.versions.values()])
		
	def get_config(self):
		config = { 'versions' : self.versions }
		
	@staticmethod
	def from_config(config):
		assert 'versions' in config
		handler = VersionsHandler()
		handler.versions = config['versions']
		return handler
'''
Predefined saving methods
'''

def save_plt(fig,path,*args,**kwargs):
	assert isinstance(fig,plt_Figure), type(fig)
	fig.savefig(path,*args,**kwargs)
	
def save_keras(model,path):
	assert isinstance(model,keras_Model), type(model)
	save_model(model,path)
	
def save_str(message,path):
	with open(path,'w') as output:
		output.write(str(message))
		
def save_numpy(arr,path):
	assert isinstance(arr,list) or isinstance(arr,ndarray), type(arr)
	np_save(path,arr)
	
def save_json(d,path):
	assert isinstance(d,dict), type(d)
	json.dump(d,path,indent = 1, pretty = True, verbose = False)