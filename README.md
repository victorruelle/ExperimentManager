# ExperimentManager

Thoughtless and all-round experiment manager for Python. ExperimentManager can easily be used to :

- Manage saving and loading directories for all your experiment files with automatic verisonning and logging.
- Record the output of your experiment and save all source files for more reproductability.
- Save (almost) any object without having to worry about anything.
- Log all your metrics thoughtlessly.
- Manage, edit and inject configuration dictionnaries directly into specified functions
- Encapsulate individual runs within your experiment. Any function can be used to create a Run; this will automatically generate a new run directory in ```saved_runs``` with dedicated ```saved_files``` and ```saved_metrics```  directories as well as a specific log file.

## Disclaimer

This is a beta version. It is stable within my testing environment (Ubuntu with specific library verisons) but has not been tested on others. 

For those familiar with the Sacred library, this project stems from their experiment manager but ambitions to correct some behavior problems (mentionned in their Issues) while allowing for better and more flexible feature and doing everything locally (without relying on other database managers or UIs which can be unflexible or tricky to install in specific environments). The only part of their code that is used here is the function signature capture.

## Requirements

This beta version runs with Tensorflow 1.13 and Keras 2.2.4 (used for Tensorboard and model Saving features). Earlier versions are not tested.

## Usage

To create an Experiment, you only need to add the following lines in your main file:

```Python
from ExperimentManager import createExperiment
manager = createExperiment('my first experiment')
```
There are many parameters that can be specified when creating an Experiment, the main ones are:

- name : name for the experiment. Will be used for creating the save directory, if needed.
- experiments_dir : the optionnal parent dir in which you want the manager to save its runs.
- project_dir : the parent directory of the code that is used to run the experiments. This is mostly used to backup the source code for more reproductability. If not provided, will use the parent dir of the file that called the init.
- load_dir : directory used for easier imports, it will be prefixed on all paths generated using manager.get_load_path
- verbose : 0,1 or 2. 1 will add some internal logs in experiment_info.log while 2 will log details on every internal function call in debug.log  (only use this to test the behavior of this class, it slows the process down by a lot!)
- tensorboard : True or False, log to tensorboard events when using metric logging methods
- ghost : True or False (default is False). When True, this will disable all saving and logging features, not a single directory or file will be created. This is usefull when running tests.


### Managing directories

Creating an Experiment Manager will automatically generate the following directory structure:

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
-------  debug.log
-------  stdout_capture.log
```

Notice that the manager_experiments direcotry was created in the directory as the source code. More precisely, if no experiment_dir is specified at initialisation time, the directory will be that containing the code that called ExperimentManager.createManager. 

All created directories have rather straight-forward goal. Saved runs contains information about runs that are conducted during the experiment using for instance the ```manager.run``` command. The pros of using this method are explained in the Runs section below.

The path to every directory is an attribute of the manager so you can access it anytime. In particular, the "my first experiment DATETIME" directory can be accessed with ```manager.experiment_dir```.

To access your experiment manager in any file, simply use the getExperiment method of ExperimentManager. It will recover the active experiment manager : ```ExperimentManager.getExperiment()```.

### Reproductability and Control

By default, your experiment manager will also save a copy of all the projects source files (.py) in ```saved_sources``` and capture the stdout in a dedicated logger ('stoud_capture.log'). This is usually enough to get a firm grasp of any past experiment and reproduce its results.

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

New saving methods can easily be added, refer to the add_saver methods doc.

### Logging metrics

Experiment Manager supports CSV loggin of scalars and Tensorboard logging of scalars and histograms.

Just use ```manager.log_scalar(metric_name,value)``` and ExperimentManager will again detect the current run and save the metrics, versioning the name if necessary. An optional ```step``` argument can be added after ```value```, by default, steps will be auto-incremented 0-based integers. Unless manager.tensorboard is set to false, logging scalars will log to a csv in the runs or global metrics directory and also log to the tensorboard directory. Metric_name is used to name the csv file as well as the header for the value column in the CSV.

For logging several metrics in a single CSV, use ```manager.log_scalars(file_name,values,header,step=None)```.

Logging a historgram is done exactly the same way ```manager.log_histrogram(name, values, step, bins=1000)``` (remember that histograms are only logged to tensorboard, not as CSV which would be too heavy; hence if tensorboard support is disabled, this will do nothing).

### Configurations

Configurations are a great way to manage all your experiment parameters in one place (a json file or dictionnary). ExperimentManager has a dedicated configuration dictionnary for every run in addition to a global configuration dictionnary. For hand-designated functions, your manager will inject it's configuration parameters by changing the function's signature (overwriting default values).

To add a configuration dictionnary, just use ```manager.add_config(dictionnary)``` (json file support coming soon). The current run or the general configuration dictionnary will be updated using the input dictionnary. If a run configuraiton dictionnary has fields in common with the general dictionnary, the run's options will always prevail (within that run only of course!).

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
- Use ```manager.add_command(function)``` and the same running method. This has the benefit of not needing to modify any part of your code (by adding @manager.command) but comes at the cost of losing configuration injections.

Note that the command decorator also calls the capture decorator (and thus performs configuration injections).

## Things to test

- [x] Checks the parameter injection. Seems to not work, maybe because of the max_depth feature (reproduce : ghost = True).
- [x] The metrics logging. Auto increment.
- [x] Make sure that run_id is also picked up when running with run_existing!
- [x] Thorough check of the new get_options
- [x] The auto getLogger feature
- [x] Tensorboard support and log_scalar/log_scalars distinction
- [x] Regex for add_project_sources

## Things to work on

- [x] createExperiment / getExperiment need to take names! You should be able to run multiple experiments at the same time. Automatic detection using Experiment IDs as locals at the very root!
- [x] Support saving with replacement
- [x] Add distribution support for logging (tensorboard)
- [x] Add info/war/error methods that will get_call_id to use a run's specific logger : logs to run file and prints using a specific run format
- [x] Replace skip_dirs and such with simple regex for better use
- [x] Create API for loading experiments ? or remove backend support.
- [ ] (Add json support for add_config)
- [ ] (Add config decorator for easier configs)
- [ ] (Add automain and main decorators)
- [x] Integrate visualisation tools for saved metrics
- [x] Add scalar logging of multiple metrics on a same axis
- [x] Add option to overwrite existing file when saving
- [x] Add support for load dir!
- [x] Change the name minisacred_debug.log
- [x] fix the stoud capturing flush method, was going crazy when I did manager.main_logger.info even though main logger had been renamed internally to logger
- [x] Improve the main loggers, I want different levels of INFO (customize) to make some messages stick out more (eg: start and end of a command!)
- [x] create a smarter metrics logging method, should at least support auto-indexing of values. Using a class with time etc.
- [x] add tensorboard support and add all the same metrics logging functions.
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
