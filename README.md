# ExperimentManager

Thoughtless and all-round experiment manager for Python

ExperimentManager does not support concurrency! When initializing an ExperimentManager instance, a specific sub-directoy is built in a specified experiments directory. No other processes should change the structure of this experiments directory. 

## Things to work on

- [ ] fix the stoud capturing flush method, was going crazy when I did manager.main_logger.info even though main logger had been renamed internally to logger
- [ ] create a smarter metrics logging method. Using a class with time etc.
- [ ] add tensorboard support
- [ ] add_config : add support for specific values in prefix ? not just dictionaries. 
- [ ] improve the efficiency of get_call_id, I could record the deepest stack level when capturing functions to avoid going throug the entire stack everytime. Also pass ids in nested function calls whenever possible to avoid unnecassary calls.
- [ ] implement self.ghost, I've bypassed it sometimes for now
- [ ] add a method to create a run so that you can do self.run with the same runner multiple times
- [ ]  Handle or prevent nested calls to ExperimentManager.run (the id found will be that of the parent caller as of now).
- [ ] Always make sure to add the run_id when logging for : save, add_config, run, etc.
- [ ] Fix the name of captured commands/functions. It still doesn't seem right.
- [ ] Implement add_sources. Code from polyrely should work easily.
