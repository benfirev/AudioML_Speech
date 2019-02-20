import numpy as np
import librosa
import os
from django.conf import settings
import tensorflow as tf
import keras
from speech.models import AudioClip,ModelWeights
from speech.speechFS import get_ac_instance
from tempfile import NamedTemporaryFile
import uuid
import boto3
from decouple import config
import datetime
from background_task import background
from django.utils.timezone import utc

max_pad_len = 200
m_mfcc = 128

def detect_from_file(file_guid):
    prediction = predict(file_guid)
    tf.reset_default_graph()
    return(prediction)

def predict(file_guid):
    data_shape = [max_pad_len,m_mfcc]
    model = get_nn_model(data_shape)
    load_weights_to_model(model)
    x_pred = np.ndarray(shape=(1,m_mfcc,max_pad_len),dtype="float")
    x_pred[0] = extract_mfcc(file_guid,max_pad_len,m_mfcc)
    prediction_arr = model.predict(x_pred)
    languages = ["Hebrew","English"]
    languages_prediction = languages[np.argmax(prediction_arr)]
    keras.backend.clear_session()
    return(languages_prediction)

def get_train_data():
    max_train_capacity_per_lang = 1000
    train_amount = np.min([AudioClip.objects.filter(lang="Hebrew").count(),AudioClip.objects.filter(lang="English").count(),max_train_capacity_per_lang])
    x_train = np.ndarray(shape=(train_amount*2,m_mfcc,max_pad_len),dtype="float")
    y_train = np.ndarray(shape=(train_amount*2,1),dtype="int32")
    heb_clips = AudioClip.objects.filter(lang="Hebrew").order_by('?')
    eng_clips = AudioClip.objects.filter(lang="English").order_by('?')
    for i in range(train_amount):
        x_train[2*i] = extract_mfcc(heb_clips[i].guid,max_pad_len,m_mfcc)
        x_train[(2*i)+1] = extract_mfcc(eng_clips[i].guid,max_pad_len,m_mfcc)
        y_train[2*i] = 0
        y_train[(2*i)+1] = 1
    return x_train,y_train

@background
def train(): 
    x_train,y_train = get_train_data()
    data_shape = [max_pad_len,m_mfcc]
    model = get_nn_model(data_shape)
    model.fit(x_train, y_train, epochs=config("TRAIN_EPOCHS",cast=int) ,shuffle=True)
    save_weights_from_model(model)
    keras.backend.clear_session()
    delete_old_sound_files()

#train every X predictions
def decice_if_train():
    num_of_saved = count_saved_data()
    if(num_of_saved % config("WHEN_TRAIN",cast=int) == 0):
        train()
        delete_old_sound_files()  

#returns model with specific structure
def get_nn_model(data_shape):
    model = keras.Sequential([
        keras.layers.Flatten(input_shape=(data_shape[1],data_shape[0])),
        keras.layers.BatchNormalization(),
        keras.layers.Dense(64, activation=tf.nn.relu),
        keras.layers.Dense(64, activation=tf.nn.relu),
        keras.layers.Dense(2, activation=tf.nn.softmax)
    ])

    model.compile(optimizer=tf.train.AdamOptimizer(), 
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy'])

    return model

def count_saved_data():
    num_of_heb_files = AudioClip.objects.filter(lang="Hebrew").count()
    num_of_eng_files = AudioClip.objects.filter(lang="English").count()
    return (num_of_eng_files + num_of_heb_files)    



def extract_mfcc(file_name, max_len=11,m_mfcc_=64):
    ac = get_ac_instance(_guid=file_name)
    s3 = boto3.resource('s3', aws_access_key_id=config('AWS_ACCESS_KEY_ID') , aws_secret_access_key= config('AWS_SECRET_ACCESS_KEY'))
    bucket = s3.Bucket('audioml-bucket')
    _object = bucket.Object('media/'+ file_name)
    f = NamedTemporaryFile(delete=False)
    _object.download_fileobj(f)
    f.close()
    wave, sr = librosa.load(f.name)
    os.remove(f.name)

    wave,index = librosa.effects.trim(wave)
    wave = librosa.core.to_mono(wave)
    wave = librosa.core.resample(wave,sr,16000)

    mfcc = librosa.feature.mfcc(wave, sr=16000,n_mfcc=m_mfcc_,norm='ortho')

    # If maximum length exceeds mfcc lengths then pad the remaining ones
    if (max_len > mfcc.shape[1]):
        pad_width = max_len - mfcc.shape[1]
        mfcc = np.pad(mfcc, pad_width=((0, 0), (0, pad_width)), mode='constant')
    # Else cutoff the remaining parts
    else:
        mfcc = mfcc[:, :max_len]
    #print('***************************************')
    #print(mfcc)
    #print('***************************************')
        
    return mfcc

def load_weights_to_model(model):

    num_of_weights = ModelWeights.objects.filter(is_ready=True).count()
    if(num_of_weights > 0):
        mdl = ModelWeights.objects.filter(is_ready=True).order_by('-uploaded_at').first()
        weights_nparr = np.load(mdl.file_weights.file)
        model.set_weights(weights_nparr)
    
    

def save_weights_from_model(model):
    #model.save_weights('my_model_weights.h5') # oldway
    model_weights =  model.get_weights()
    with NamedTemporaryFile() as tmpfile:
        np.save(tmpfile,model_weights)    
        mdl = ModelWeights.objects.create()
        mdl.file_weights.save(str(uuid.uuid4()),tmpfile)
        mdl.is_ready = True
        mdl.save()
        tmpfile.close()
    delete_old_train_weights()

def delete_old_sound_files():
    undecided_clips = AudioClip.objects.filter(lang="Undecided")
    
    for clip in undecided_clips:
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        hours_passed = ((now - clip.uploaded_at).total_seconds()) / (60 * 60) 
        if(hours_passed > 5):
            clip.delete()

def delete_old_train_weights():
    while(ModelWeights.objects.count() > 10):
        ModelWeights.objects.filter(is_ready=True).order_by('uploaded_at').first().delete()