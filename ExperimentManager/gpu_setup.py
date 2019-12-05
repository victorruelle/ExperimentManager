import os

try:
    import tensorflow as tf
    from keras import backend as K


    '''
    TENSORFLOW + KERAS SETUP OPTIONS
    '''

    def keras_setup(allow_growth = True, memory_fraction_per_gpu = 1):

        with tf.device('/gpu:1'):
            config = tf.ConfigProto()
            setattr(getattr(config,'gpu_options'),'allow_growth',allow_growth) # hack to avoid VS code form warning me that config has no attribute gpu_options even though it does
            setattr(getattr(config,"gpu_options"),'per_process_gpu_memory_fraction',memory_fraction_per_gpu)
            session = tf.Session(config=config)
            K.set_session(session)

except:

    def keras_setup(*args,**kwargs):
        raise Exception("Called create session even though tensorflow and/or keras is not installed")

def cuda_setup(devices = None):
    if devices is not None:
        os.environ["CUDA_VISIBLE_DEVICES"]= str(devices)[1:-1]