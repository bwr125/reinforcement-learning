# coding: utf-8

# This example follows
# http://www.danielslater.net/2016/03/deep-q-learning-pong-with-tensorflow.html

# We use q-learning. We approximate the q function with a neural network using
# tensorflow.

import tensorflow as tf
import random
import numpy as np
import gym
from collections import deque

# Set up the action space
ACTIONS = [0,2,3]
NUM_ACTIONS = len(ACTIONS)

# The number of frames to use as our state
STATE_FRAMES = 4

# The size to resize the frame to
RESIZED_SCREEN_X, RESIZED_SCREEN_Y = 80, 80

# Epsilon greedy
EXPLORE_STEPS = 500000 # The total number of time steps to anneal epsilon
INITIAL_EPSILON_GREEDY = 1.0 # Initial epsilon
FINAL_EPSILON_GREEDY = 0.05 # Final epsilon

OBSERVATION_STEPS = 50000 # Time steps to observe before training
MEMORY_SIZE = 500000

# The minibatch size to train with
MINI_BATCH_SIZE = 100

# The discount factor to use
DISCOUNT_FACTOR = 0.99

# The number of rewards to compute the average with
NUM_REWARDS_FOR_AVERAGE = 100

def create_network():
    conv1_W = tf.Variable(tf.truncated_normal([8, 8, STATE_FRAMES, 32],
        stddev=0.01))
    conv1_b = tf.Variable(tf.constant(0.01, shape=[32]))

    conv2_W = tf.Variable(tf.truncated_normal([4, 4, 32, 64], stddev=0.01))
    conv2_b = tf.Variable(tf.constant(0.01, shape=[64]))

    conv3_W = tf.Variable(tf.truncated_normal([3, 3, 64, 64], stddev=0.01))
    conv3_b = tf.Variable(tf.constant(0.01, shape=[64]))

    fc1_W = tf.Variable(tf.truncated_normal([256, 256], stddev=0.01))
    fc1_b = tf.Variable(tf.constant(0.01, shape=[256]))
    
    fc2_W = tf.Variable(tf.truncated_normal([256, NUM_ACTIONS], stddev=0.01))
    fc2_b = tf.Variable(tf.constant(0.01, shape=[NUM_ACTIONS]))

    input_layer = tf.placeholder("float", [None, RESIZED_SCREEN_X,
        RESIZED_SCREEN_Y, STATE_FRAMES])

    conv1 = tf.nn.relu(tf.nn.conv2d(input_layer, conv1_W, strides=[1,4,4,1],
        padding="SAME") + conv1_b)

    max1 = tf.nn.max_pool(conv1, ksize=[1,2,2,1], strides=[1,2,2,1],
            padding="SAME")

    conv2 = tf.nn.relu(tf.nn.conv2d(max1, conv2_W, strides=[1,2,2,1],
        padding="SAME") + conv2_b)

    max2 = tf.nn.max_pool(conv2, ksize=[1,2,2,1], strides=[1,2,2,1],
            padding="SAME")

    conv3 = tf.nn.relu(tf.nn.conv2d(max2, conv3_W, strides=[1,1,1,1],
        padding="SAME") + conv3_b)

    max3 = tf.nn.max_pool(conv3, ksize=[1,2,2,1], strides=[1,2,2,1],
            padding="SAME")

    flatten = tf.reshape(max3, [-1, 256])

    fc1 = tf.nn.relu(tf.matmul(flatten, fc1_W) + fc1_b)

    output_layer = tf.matmul(fc1, fc2_W) + fc2_b

    return input_layer, output_layer

# Train the agent
def train(tf_sess, observations, tf_input_layer, tf_output_layer,
        tf_train_operation, tf_action, tf_target):
    # Sample a minibatch to train on
    mini_batch = random.sample(observations, MINI_BATCH_SIZE)

    states = [d['state'] for d in mini_batch]
    actions = [d['action'] for d in mini_batch]
    rewards = [d['reward'] for d in mini_batch]
    next_states = [d['next_state'] for d in mini_batch]
    agent_expected_reward = []

    agent_reward_per_action = tf_sess.run(tf_output_layer,
            feed_dict={tf_input_layer : next_states})

    for i in xrange(len(mini_batch)):
        if mini_batch[i]['terminal']:
            # This was a terminal frame
            agent_expected_reward.append(rewards[i])
        else:
            agent_expected_reward.append( rewards[i] + DISCOUNT_FACTOR * \
                    np.max(agent_reward_per_action[i]))

    one_hot_actions = compute_one_hot_actions(actions)

    # Learn that these actions in these states lead to this reward
    tf_sess.run(tf_train_operation, feed_dict={
        tf_input_layer: states,
        tf_action: one_hot_actions,
        tf_target: agent_expected_reward})

def compute_one_hot_actions(actions):
    one_hot_actions = []
    for i in xrange(len(actions)):
        one_hot = np.zeros([NUM_ACTIONS])
        one_hot[ACTIONS.index(actions[i])] = 1
        one_hot_actions.append(one_hot)
    return one_hot_actions

def pong_deep_q_learn():

    # Create tensorflow network
    tf_sess = tf.Session()
    tf_input_layer, tf_output_layer = create_network()
    tf_action = tf.placeholder("float", [None, NUM_ACTIONS])
    tf_target = tf.placeholder("float", [None])

    tf_readout_action = tf.reduce_sum(tf.mul(tf_output_layer, tf_action),
            reduction_indices=1)

    tf_cost = tf.reduce_mean(tf.square(tf_target - tf_readout_action))

    tf_train_operation = tf.train.AdamOptimizer(1e-6).minimize(tf_cost)

    tf_sess.run(tf.initialize_all_variables())

    epsilon_greedy = INITIAL_EPSILON_GREEDY

    observations = deque()
    nonzero_rewards = deque()
    actions = []

    env = gym.make('Pong-v0')
    obs = env.reset()

    # Compute the first state
    current_state = compute_state(None, obs)
    
    # Enter loop over number of time steps
    t = 0
    while True:
        # Compute action
        action = compute_action(tf_sess, tf_input_layer, tf_output_layer,
                current_state, epsilon_greedy)

        # Take a step with action
        obs, reward, terminal, info = env.step(action)

        # Update the current and next states
        next_state = compute_state(current_state, obs)

        # Record transitions
        observations.append({'state': current_state, 'action':
            action, 'reward': reward, 'next_state': next_state,
            'terminal': terminal})

        # Keep track of nonzero rewards so we can compute an average
        if reward != 0:
            nonzero_rewards.append(reward)

        # Ensure we don't keep track of nonzero rewards for more than specified
        if len(nonzero_rewards) > NUM_REWARDS_FOR_AVERAGE:
            nonzero_rewards.popleft()

        # Print out rewards
        if (t % 100 == 0) and len(nonzero_rewards) > 0:
            print("Average reward: {}, time: \
                    {}".format(np.mean(nonzero_rewards), t))

        # Ensure we don't go over our memory size
        if len(observations) > MEMORY_SIZE:
            observations.popleft()

        # Train if we have reached the number of observation steps
        if len(observations) > OBSERVATION_STEPS:
            train(tf_sess, observations, tf_input_layer, tf_output_layer,
                    tf_train_operation, tf_action, tf_target)
    
        # Anneal epsilon for epsilon-greedy strategy
        if epsilon_greedy > FINAL_EPSILON_GREEDY and len(observations) > \
                OBSERVATION_STEPS:
            epsilon_greedy -= (INITIAL_EPSILON_GREEDY - FINAL_EPSILON_GREEDY) \
                    / EXPLORE_STEPS

        # If terminal, then reset the environment
        if terminal:
            obs = env.reset()
            
            # Compute the first state
            current_state = compute_state(None, obs)

        # Update t
        t += 1
        

# If current_state is None then just repeat the observation STATE_FRAMES times.
# Otherwise, remove the first frame, and append obs to get the new current
# state.
def compute_state(current_state, obs):
    # First preprocess the observation
    obs = preprocess(obs)

    if current_state is None:
        state = np.stack(tuple(obs for i in range(STATE_FRAMES)), axis=2)
    else:
        # obs is two-dimensional, so insert a dummy third dimension
        state = np.append(current_state[:,:,1:], obs[:,:,np.newaxis], axis=2)
    return state

# Preprocess the observation to remove noise. Specific to pong.
def preprocess(obs):
    # Convert to float
    obs = obs.astype('float32')
    # Crop screen
    obs = obs[34:194,:,0]
    # Downsize screen
    obs = obs[::2,::2]
    # Erase background
    obs[obs == 144] = 0
    obs[obs == 109] = 0
    # Set everything else to 1
    obs[obs != 0] = 1
    return obs

def compute_action(tf_sess, input_layer, output_layer, current_state,
        epsilon_greedy):
    new_action = np.zeros([NUM_ACTIONS])

    if random.random() <= epsilon_greedy:
        # Choose an action randomly
        action_index = random.randrange(NUM_ACTIONS)
    else:
        # Choose an action given our current state
        q_function = tf_sess.run(output_layer, feed_dict={input_layer: \
            [current_state]})[0]
        action_index = np.argmax(q_function)

    # Return the action at action_index
    return ACTIONS[action_index]

pong_deep_q_learn()
