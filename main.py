from experiment import *

manager = ExperimentManager('test')
#pprint_dict(manager.__dict__)

@manager.capture
def a_function(name,value = 0):
	print('name',name)
	print('value',value)
	
	
@manager.command
def a_command(name,value = 0):
	print('Entering command a_command')
	print('name',name)
	print('value',value)
	manager.save([1,2,3,4,5],'a_list')
	manager.log_scalar('time',1,0)
	manager.log_scalar('time',1,1)
	manager.log_scalar('time',1,2)
	manager.log_scalar('time',1,3)
	manager.log_scalar('time',1,4)
	a_function(**{})
	
@manager.command
def test_sacred():
		
	manager.run('a_command', update_dict = {'name':'Pierre'})

	manager.add_config( {'name':'Victor'} )

	a_function()
	
def test():
	
	from utils import get_options
	
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
	
	from utils import pprint_dict
	
	d = get_options(main_dict,run_dict,prefixes)
	pprint_dict(d, name = "result of the get_options call")
	
	return d

if __name__ == "__main__":
	print("Hi, let's start an experiment!")
	manager.logger.info("Here's a log message")
	manager.std_logger.info("Here's a log message from the std logger")
	d = test()
	manager.save(d,'options_dict')
	manager.add_config(d)
	manager.run('a_command')
	manager.run('a_command',update_dict= { "name" : "Pierre" })
	manager.run('test_sacred')
	print("Bye!")
	manager.close()
	print('Should not be captured')