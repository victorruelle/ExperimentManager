# ExperimentManager

Thoughtless and all-round experiment manager for Python. ExperimentManager can easily be used to :

- Manage saving and loading directories for all your experiment files with automatic verisonning and logging.
- Record the output of your experiment and save all source files for more reproductability.
- Save (almost) any object without having to worry about anything.
- Log all your metrics thoughtlessly.
- Manage, edit and inject configuration dictionnaries directly into specified functions
- Encapsulate individual runs within your experiment. Any function can be used to create a Run; this will automatically generate a new run directory in ```saved_runs``` with dedicated ```saved_files``` and ```saved_metrics```  directories as well as a specific log file. 

## Usage

### Managing directories

To create an Experiment, you only need to add the following lines in your main file:

```Python
from ExperimentManager import createExperiment
manager = createExperiment('my first experiment')
```

This will automatically create the following directory structure:

```bash
./
-- (your_source_code)
-- managed_experiments/
---- my first experiment DATETIME/
-------  saved_files/
-------  saved_sources/
-------  saved_metrics/
-------  saved_runs/
-------  experiment_info.log
-------  minisacred_debug.log
-------  stdout_capture.log
```

The path to every directory is added as attribute to the manager so you can access it anytime. In particular, the "my first experiment DATETIME" directory can be accessed with ```manager.experiment_dir```.

To access your experiment manager in any file, simply use the getExperiment method of ExperimentManager. It will recover the active experiment manager.

By default, your experiment manager will also save a copy of all the projects source files (.py) in ```saved_sources``` and capture the stdout in a dedicated logger ('stoud_capture.log')

### Saving, like never before

At any point, you can simply call ```manager.save(object,name)``` and ExperimentManager will :

- Detect which folder it should save in : the general ```saved_files``` directory in ```my frist experiment DATETIME``` or in a specific run subdirectory.
- Detect the saving method that should be used.
- Version the name if needed.

Implemented saving methods cover the following data types:

- Lists and dicts
- Numpy arrays
- Tensorflow tensors (if they can be evaluated)
- Keras models
- Matplotlib figures

New saving methods can easily be added, refer to the add_saver method's doc.

### Logging metrics

For now, only scalar metrics are implemented, many more types will soon arrive. Just use ```manager.log_scalar(metric_name,value)``` and ExperimentManager will do all the same work as for saving methods automatically. An optional ```step``` argument can be added after ```value```, by default, steps will be auto-incremented 0-based integers.

### Configurations

Configurations are a great way to manage all your experiment parameters in one place (a json file or dictionnary). ExperimentManager has a dedicated configuration dictionnary for every run in addition to a global configuration dictionnary. For hand-designated functions, your manager will inject it's configuration parameters by changing the function's signature (overwriting default values).

To add a configuration dictionnary, just use ```manager.add_config(dictionnary)``` (json file support coming soon). The current run and the general configuration dictionnary will be updated using the input dictionnary. If a run configuraiton dictionnary has fields in common with the general dictionnary, the run's options will always prevail (within that run only of course!).

To designate a function that should receive configuration values, add the ```@manager.capture``` decorator. You can specify exactly which fields should be injected using the prefixes parameter. Here's an example: 

```Python

manager = createManager('test')

config1 = { 
		"name" : "Victor",
		"status" : 1,
		"details" : {
			"age" : 22,
			"towns" : {
				0 : "Brussels",
				1 : "Paris"
				}
			}	
		}

manager.add_config(config1) #this will update the general configurations dict since we are not in a run

@manager.capture()
def function1(time,name,details):
    pass

@manager.capture()
def function2(name,status,details):
    pass

@manager.capture(prefixes=['name','details.towns','details.age,'details'])
def function2(names,towns,details):
    pass
```

Is equivalent to:

```Python
def function1(time,name='Victor',details={"age" : 22,"towns" : {0 : "Brussels",1 : "Paris"}}):
    pass

def function2(name='Victor',status=1,details={"age" : 22,"towns" : {0 : "Brussels",1 : "Paris"}}):
    pass

def funciton3(name='Victor',towns={0 : "Brussels",1 : "Paris"},age=22,details={"age" : 22,"towns" : {0 : "Brussels",1 : "Paris"}}):
    pass
```

As you can see, not all function parameters need to be covered. If you add **kwargs, all the keys will be added.

### Runs

To take full advantage of the ExperimentManager, run your tasks using the run method of your manager.
ExperimentManager will automatically detect which run is active when using saving and logging methods so that your files will always end up in the right place. To launch a run you have two options:

- Add a ```@manager.command``` decorator to a function and run it using ```manager.run(the_name_of_the_function)```.
- Use ```manager.add_command(function)``` and the same running method.

The command decorator also calls the capture decorator.

## Things to test

- [x] Checks the parameter injection. Seems to not work, maybe because of the max_depth feature (reproduce : ghost = True).
- [x] The metrics logging. Auto increment.
- [x] Make sure that run_id is also picked up when running with run_existing!
- [x] Thorough check of the new get_options
- [x] The auto getLogger feature

## Things to work on

- [x] createExperiment / getExperiment need to take names! You should be able to run multiple experiments at the same time. Automatic detection using Experiment IDs as locals at the very root!
- [ ] Support saving with replacement
- [ ] Add info/war/error methods that will get_call_id to use a run's specific logger : logs to run file and prints using a specific run format
- [ ] Replace skip_dirs and such with simple regex for better use
- [ ] Create API for loading experiments ? or remove backend support.
- [ ] Add json support for add_config.
- [ ] Add config decorator for easier configs
- [ ] Add automain and main decorators
- [ ] Integrate visualisation tools for saved metrics
- [ ] Add scalar logging of multiple metrics on a same axis
- [ ] Add option to overwrite existing file when saving
- [ ] Add support for load dir!
- [ ] Change the name minisacred_debug.log
- [x] fix the stoud capturing flush method, was going crazy when I did manager.main_logger.info even though main logger had been renamed internally to logger
- [ ] Improve the main loggers, I want different levels of INFO (customize) to make some messages stick out more (eg: start and end of a command!)
- [x] create a smarter metrics logging method, should at least support auto-indexing of values. Using a class with time etc.
- [ ] add tensorboard support and add all the same metrics logging functions.
- [x] add_config : add support for specific values in prefix ? not just dictionaries. 
- [x] improve the efficiency of get_call_id, I could record the deepest stack level when capturing functions to avoid going throug the entire stack everytime. Also pass ids in nested function calls whenever possible to avoid unnecassary calls.
- [x] implement self.ghost, I've bypassed it sometimes for now
- [x] add a method to create a run so that you can do self.run with the same runner multiple times
- [x] Handle nested calls to ExperimentManager.run, last id should be kept, not the first one.
- [x] Always make sure to add the run_id when logging for : save, add_config, run, etc.
- [x] Fix the name of captured commands/functions. It still doesn't seem right.
- [x] Implement add_sources. Code from polyrely should work easily.
- [x] Improve log_locals : should not need to call log_locals(locals()) but just log_locals() and let log_locals go up one level to find the locals
- [x] Fix save project ressources : I must check more thouroughly if the current path is not in the experiments dir when doing a walk. The name of the current dir alone is not enough! Need to exclude all those whose full path contains the excluse folders.
- [x] Improve all the try statements : add except to print the stack trace when theres an error. Do not allow silent fails!