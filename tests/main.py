from ExperimentManager.experiment import ExperimentManager

manager = ExperimentManager('test',ghost=False)

@manager.capture
def printing_function(name,value = 0):
	print('Entering printing function')
	print('name',name)
	print('value',value)
	print('Exiting printing function')
	
	
@manager.command
def metrics_logging(name,value = 0):
	print('Entering metrics_logging command')
	for i in range(50):
		manager.log_scalar('time',i**2,i)
	for i in range(50):
		manager.log_scalar('time auto_increment',i**2)
	print('Exiting metrics_logging command')

	
@manager.capture(prefixes=['details.towns','details.age'])
def saving(towns,age):
	print('Entering saving, towns is {} and age is {}'.format(towns,age))
	print('Saving the towns dict without any parameters')
	manager.save(towns,'my towns')
	print('Saving the towns dict with a txt extension')
	manager.save(towns,'my towns.txt')
	import numpy as np
	an_array = np.random.uniform((32,4,2))
	manager.save(an_array,'a numpy array')

@manager.command
def changing_configs():
	print('Entering command changing config')
	print('Current run id is {}'.format(manager.get_call_id()))
	print('Config is : {}'.format(manager.config))
	print('Running print without any change')
	printing_function(**{})
	print('Updating confing')
	manager.add_config( {'name':'A local config Victor'} )
	print('Config is : {}'.format(manager.config))
	printing_function(**{})
	print('Updating confing')
	manager.add_config( {'name':'A global config Victor'}, -1 )
	print('Config is : {}'.format(manager.config))
	printing_function(**{})
	print('Exiting command changing config')


def merging_configs():
	
	from ExperimentManager.utils import get_options
	
	main_dict = { 
		"name" : "Julie",
		"value" : 1,
		"details" : {
			"age" : 22,
			"towns" : {
				0 : "Brussels",
				1 : "Paris"
				}
			}	
		}
		
	run_dict = { 
		"details" : {
			"age" : 21,
			"towns" : {
				0 : "Tel-Aviv"
				}
			}	
		}
		
	prefixes = None #["details.towns"] #,"details.age"]
	
	from ExperimentManager.utils import pprint_dict
	
	d = get_options(main_dict,run_dict,prefixes)
	pprint_dict(d, name = "result of the get_options call")
	
	return d


if __name__ == "__main__":
	print("Hi, let's start an experiment!")
	manager.logger.info("Here's a log message")
	
	d = { 
		"name" : "Julie",
		"value" : 1,
		"details" : {
			"age" : 22,
			"towns" : {
				0 : "Brussels",
				1 : "Paris"
				}
			}	
		}
	
	manager.add_config(d)
	raise Exception('Hi there. Lets stop')
	print('Running command changing_configs')
	manager.run('changing_configs')
	print('Running command changing_configs with Pierre update_dict')
	manager.run('changing_configs',update_dict= { "name" : "Pierre" })
	print('Running metrics_logging')
	manager.run('metrics_logging')
	saving(**{})
	print("Bye!")
	manager.close()
	print('Should not be captured')