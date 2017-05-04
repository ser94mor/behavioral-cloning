import os
import zipfile
import cv2
import numpy as np
import pandas as pd

from keras.models import Sequential
from keras.layers import Flatten, Dense, Lambda
from keras.layers.convolutional import Convolution2D, Cropping2D
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle


def generator(samples, batch_size=128):
    num_samples = len(samples)
    while 1: # Loop forever so the generator never terminates
        shuffle(samples)
        for offset in range(0, num_samples, batch_size):
            batch_samples = samples[offset:offset+batch_size]
            images = []
            angles = []
            for batch_sample in batch_samples:
                center_image = cv2.imread(data['CENTER_IMAGE'][batch_sample])
                center_angle = float(data['STEERING_ANGLE'][batch_sample])
                images.append(center_image)
                angles.append(center_angle)
            # trim image to only see section with road
            X_train = np.array(images)
            y_train = np.array(angles)

            yield shuffle(X_train, y_train)


# extract augmented data archive if not already extracted
if not (os.path.isdir("data_augmented") and os.path.exists("data_augmented.csv")):
    print("unzipping data")
    zip_ref = zipfile.ZipFile("data_augmented.zip", 'r')
    zip_ref.extractall(".")
    zip_ref.close()

# define generator which will help to overcome problems arising while working with a large amounts of data
data = pd.read_csv("data_augmented.csv").to_dict(orient='list')

n_records = len(data['STEERING_ANGLE'])

train_samples, validation_samples = train_test_split(np.array([i for i in range(n_records)]), test_size=0.2)
train_generator = generator(train_samples, batch_size=128)
validation_generator = generator(validation_samples, batch_size=128)

# construct neural network model
# using the model from
#                http://images.nvidia.com/content/tegra/automotive/images/2016/solutions/pdf/end-to-end-dl-using-px.pdf

# model parameters
steering_angle_correction = 0.2

# the model's type is sequential
model = Sequential()

# crop input image to leave only useful information - the road
# the trees, sky and the car's hood will be removed
model.add(Cropping2D(cropping=((70, 25), (0, 0)), input_shape=(160, 320, 3)))

# normalize input image
model.add(Lambda(lambda x: (x / 255.0) - 0.5))

# add 5 convolution layers
model.add(Convolution2D(24, 5, 5, subsample=(2, 2), activation='relu'))
model.add(Convolution2D(36, 5, 5, subsample=(2, 2), activation='relu'))
model.add(Convolution2D(48, 5, 5, subsample=(2, 2), activation='relu'))
model.add(Convolution2D(64, 3, 3, activation='relu'))
model.add(Convolution2D(64, 3, 3, activation='relu'))

# flatten output of the last convolution layer
model.add(Flatten())

# add some fully connected layers
model.add(Dense(100))
model.add(Dense(50))
model.add(Dense(10))
model.add(Dense(1))  # model has only one output - steering angle

print('starting training')

model.compile(loss='mse', optimizer='adam')

model.fit_generator(train_generator,
                    samples_per_epoch=len(train_samples),
                    validation_data=validation_generator,
                    nb_val_samples=len(validation_samples),
                    nb_epoch=30,
                    verbose=1)

# save model to be able to reuse it in autonomous driving
model.save("model.h5")

