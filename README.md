# ExperimentManager

Thoughtless and all-round experiment manager for Python

ExperimentManager does not support concurrency! When initializing an ExperimentManager instance, a specific sub-directoy is built in a specified experiments directory. No other processes should change the structure of this experiments directory. 

## Things to test

- [x] Checks the parameter injection. Seems to not work, maybe because of the max_depth feature (reproduce : ghost = True).
- [x] The metrics logging. Auto increment.
- [x] Make sure that run_id is also picked up when running with run_existing!
- [ ] Thorough check of the new get_options

## Things to work on

- [ ] Add config decorator for easier configs
- [ ] Add automain and main decorators
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