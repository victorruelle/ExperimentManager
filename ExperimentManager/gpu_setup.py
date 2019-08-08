import os
import tensorflow as tf
from keras import backend as K


def keras_setup(devices = None, allow_growth = True, memory_fraction_per_gpu = 1):


    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
    if devices is not None:
        os.environ["CUDA_VISIBLE_DEVICES"]= str(devices)[1:-1]

    with tf.device('/gpu:1'):
        config = tf.ConfigProto()
        setattr(getattr(config,'gpu_options'),'allow_growth',allow_growth) # hack to avoid VS code form warning me that config has no attribute gpu_options even though it does
        setattr(getattr(config,"gpu_options"),'per_process_gpu_memory_fraction',memory_fraction_per_gpu)
        session = tf.Session(config=config)
        K.set_session(session)

def create_session(devices = None, allow_growth = True, memory_fraction_per_gpu = 1, graph = None):

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
    if devices is not None:
        os.environ["CUDA_VISIBLE_DEVICES"]= str(devices)[1:-1]

    with tf.device('/gpu:1'):
        config = tf.ConfigProto()
        setattr(getattr(config,'gpu_options'),'allow_growth',allow_growth) # hack to avoid VS code form warning me that config has no attribute gpu_options even though it does
        setattr(getattr(config,"gpu_options"),'per_process_gpu_memory_fraction',memory_fraction_per_gpu)
        session = tf.Session(config=config, graph=graph)
        return session