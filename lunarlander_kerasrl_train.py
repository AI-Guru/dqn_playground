import numpy as np
import gym
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam
from rl.agents.dqn import DQNAgent
from rl.policy import BoltzmannQPolicy
from rl.memory import SequentialMemory
from kerasrl_extensions import *
import sys


ENV_NAME = "LunarLander-v2"


def main():

    # Create environment and model.
    environment = create_environment(ENV_NAME)
    observation_shape = environment.observation_space.shape
    nb_actions = environment.action_space.n
    model = build_model(observation_shape, nb_actions)

    # Finally, we configure and compile our agent. You can use every built-in Keras optimizer and
    # even the metrics!
    memory = SequentialMemory(limit=100000, window_length=1)
    policy = BoltzmannQPolicy()
    # enable the dueling network
    # you can specify the dueling_type to one of {'avg','max','naive'}
    dqn = DQNAgent(model=model, nb_actions=nb_actions, memory=memory, nb_steps_warmup=10,
                   enable_dueling_network=True, dueling_type='avg', target_model_update=1e-2, policy=policy)
    dqn.compile(Adam(lr=1e-3), metrics=['mae'])

    callbacks = []
    callbacks += [TensorboardCallback()]

    # Okay, now it's time to learn something! We visualize the training here for show, but this
    # slows down training quite a lot. You can always safely abort the training prematurely using
    # Ctrl + C.
    dqn.fit(
        environment,
        nb_steps=1000000,
        visualize="visualize" in sys.argv,
        verbose=2,
        callbacks=callbacks
        )

    # After training is done, we save the final weights.
    dqn.save_weights('duel_dqn_{}_weights.h5f'.format(ENV_NAME), overwrite=True)

    # Finally, evaluate our algorithm for 5 episodes.
    dqn.test(environment, nb_episodes=5, visualize=False)


def create_environment(environment_name):
    # Get the environment and extract the number of actions.
    environment = gym.make(environment_name)
    np.random.seed(123)
    environment.seed(123)

    return environment


def build_model(observation_shape, nb_actions):
    # Next, we build a very simple model regardless of the dueling architecture
    # if you enable dueling network in DQN , DQN will build a dueling network base on your model automatically
    # Also, you can build a dueling network by yourself and turn off the dueling network in DQN.
    model = Sequential()
    model.add(Flatten(input_shape=(1,) + observation_shape))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(16))
    model.add(Activation('relu'))
    model.add(Dense(nb_actions, activation='linear'))
    model.summary()
    return model


if __name__ == "__main__":
    main()
