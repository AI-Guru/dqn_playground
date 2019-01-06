import warnings
warnings.filterwarnings("ignore")
from PIL import Image
import numpy as np
import gym
import gym_ple
from keras import models, layers, optimizers
#import keras.backend as K
from rl.agents.dqn import DQNAgent
from rl.policy import LinearAnnealedPolicy, BoltzmannQPolicy, EpsGreedyQPolicy
from rl.memory import SequentialMemory
from rl.core import Processor
from rl.callbacks import FileLogger, ModelIntervalCheckpoint, Callback
import tensorflow as tf
from collections import deque


INPUT_SHAPE = (84, 84)
WINDOW_LENGTH = 4


class FlappyBirdProcessor(Processor):
    """
    Transforms observations, state-batches and rewards of
    Flappy-Bird.
    """

    def process_observation(self, observation):
        """
        Takes an observation, resizes it and turns it into greyscale.
        """
        img = Image.fromarray(observation)
        img = img.resize(INPUT_SHAPE).convert('L')
        processed_observation = np.array(img)
        return processed_observation.astype('uint8')

    def process_state_batch(self, batch):
        """
        Normalizes a batch of observations.
        """
        processed_batch = batch.astype('float32') / 255.
        return processed_batch

    def process_reward(self, reward):
        """
        Clips the rewards.
        """
        return np.clip(reward, -1., 1.)


class TensorboardCallback(Callback):
    """
    Provides logging in TensorBoard.
    """

    def __init__(self, log_interval=1000, reward_buffer_length=10000, episode_duration_buffer_length=10000):
        self.log_interval = log_interval

        self.iterations = 0

        self.running_data = {}
        self.running_data["reward"] = deque([], maxlen=reward_buffer_length)
        self.running_data["episode_duration"] = deque([], maxlen=episode_duration_buffer_length)

        self.tensorboard_writer = tf.summary.FileWriter("tensorboard", flush_secs=5)

    def on_step_end(self, step, logs={}):
        """
        Logs data if log-interval exceeded.
        """
        self.running_data["reward"].append(logs["reward"])

        if self.iterations % self.log_interval == 0:
            for key, values in self.running_data.items():
                if len(values) > 0:
                    mean = np.mean(values)
                    self._log_scalar(key + "-mean", mean, self.iterations)

        self.iterations += 1

    def on_episode_end(self, step, logs={}):
        """
        Logs the duration of the episode.
        """
        self.running_data["episode_duration"].append(logs["nb_episode_steps"])

    def _log_scalar(self, tag, value, step):
        """
        Accesses tensorbord to log a value.
        """
        summary = tf.Summary(value=[tf.Summary.Value(tag=tag, simple_value=value)])
        self.tensorboard_writer.add_summary(summary, step)


def main():

    # Get the environment and extract the number of actions.
    environment_name = "FlappyBird-v0"
    environment = gym.make(environment_name)
    np.random.seed(666)
    nb_actions = environment.action_space.n

    # Build the model.
    model = build_model((WINDOW_LENGTH,) + INPUT_SHAPE, nb_actions)
    print(model.summary())

    # Finally, we configure and compile our agent. You can use every built-in Keras optimizer and
    # even the metrics!
    memory = SequentialMemory(limit=1000000, window_length=WINDOW_LENGTH)
    processor = FlappyBirdProcessor()

    # Select a policy. We use eps-greedy action selection, which means that a random action is selected
    # with probability eps. We anneal eps from 1.0 to 0.1 over the course of 1M steps. This is done so that
    # the agent initially explores the environment (high eps) and then gradually sticks to what it knows
    # (low eps). We also set a dedicated eps value that is used during testing. Note that we set it to 0.05
    # so that the agent still performs some random actions. This ensures that the agent cannot get stuck.
    policy = LinearAnnealedPolicy(EpsGreedyQPolicy(), attr='eps', value_max=1., value_min=.1, value_test=.05,
                                  nb_steps=1000000)

    # The trade-off between exploration and exploitation is difficult and an on-going research topic.
    # If you want, you can experiment with the parameters or use a different policy. Another popular one
    # is Boltzmann-style exploration:
    # policy = BoltzmannQPolicy(tau=1.)
    # Feel free to give it a try!

    dqn = DQNAgent(model=model, nb_actions=nb_actions, policy=policy, memory=memory,
                   processor=processor, nb_steps_warmup=50000, gamma=.99, target_model_update=10000,
                   train_interval=4, delta_clip=1.)
    dqn.compile(optimizers.Adam(lr=.00025), metrics=['mae'])

    weights_filename = 'dqn_{}_weights.h5f'.format(environment_name)

    # Okay, now it's time to learn something! We capture the interrupt exception so that training
    # can be prematurely aborted. Notice that now you can use the built-in Keras callbacks!
    checkpoint_weights_filename = 'dqn_' + environment_name + '_weights_{step}.h5f'
    log_filename = 'dqn_{}_log.json'.format(environment_name)
    callbacks = [ModelIntervalCheckpoint(checkpoint_weights_filename, interval=250000)]
    callbacks += [TensorboardCallback()]
    callbacks += [FileLogger(log_filename, interval=100)]
    dqn.fit(environment, callbacks=callbacks, nb_steps=1750000, log_interval=10000)

    # After training is done, we save the final weights one more time.
    dqn.save_weights(weights_filename, overwrite=True)

    # Finally, evaluate our algorithm for 10 episodes.
    dqn.test(environment, nb_episodes=10, visualize=False)

def build_model(input_shape, actions):
    model = models.Sequential()
    model.add(layers.Permute((2, 3, 1), input_shape=input_shape))
    model.add(layers.Convolution2D(32, (8, 8), strides=(4, 4), activation="relu"))
    model.add(layers.Convolution2D(64, (4, 4), strides=(2, 2), activation="relu"))
    model.add(layers.Convolution2D(64, (3, 3), strides=(1, 1), activation="relu"))
    model.add(layers.Flatten())
    model.add(layers.Dense(512, activation="relu"))
    model.add(layers.Dense(actions, activation="linear"))
    return model


if __name__ == "__main__":
    main()
