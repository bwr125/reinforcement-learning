# coding: utf-8

# This code works using a vanilla version of the policy-gradient method. 

import numpy as np
import random
import gym
import matplotlib.pyplot as plt
import pickle
import sys
env = gym.make('Pong-v0')

MOVE_UP = 2
MOVE_DOWN = 3

# Play with policy gradient agent, with given parameter vector
# - num_episodes: the number of episodes to run the agent
# - theta: the parameter to use for the policy
# - max_episode_length: the maximum length of an episode
def policy_gradient_agent(num_episodes, W1, W2, max_episode_length, render=True):
    for i_episode in range(num_episodes):
        episode_rewards, _, _, _ = run_episode(W1, W2, max_episode_length, render)
        print('Reward for episode:', sum(episode_rewards))

# Train an agent using policy gradients. Each episode, we sample a trajectory,
# and then estimate the gradient of the expected reward with respect to theta.
# We then update theta in the direction of the gradient.
# - num_episodes: the number of episodes to train for
# - max_episode_length: the maximum length of an episode
def train_policy_gradient_agent(num_episodes, max_episode_length,
        batch_size=10, num_hidden=10, render=False, plot=False):
    # Initialise W1, W2
    W1 = initialise_weights(80*80, num_hidden)
    W2 = initialise_weights(num_hidden, 1)

    win_history = []
    if plot:
        plt.ion()
        fig = plt.figure()
        ax1 = fig.add_subplot(1,1,1)

    # SGD with Adam
    m1 = np.zeros(np.shape(W1))
    v1 = np.zeros(np.shape(W1))
    m2 = np.zeros(np.shape(W2))
    v2 = np.zeros(np.shape(W2))

    show_state = False
    if show_state:
        plt.ion()
        f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, sharex='col', sharey='row')

    for i_episode in range(num_episodes):
        batch_rewards = []
        batch_actions = []
        batch_states = []
        batch_length = 0
        batch_results = []
        for i_batch in range(batch_size):
            # Run an episode with our current policy
            if i_batch == 0:
                render_episode = render
            else:
                render_episode = False
            episode_rewards, episode_actions, episode_states, episode_length = \
                    run_episode(W1, W2, max_episode_length, render_episode)

            batch_rewards += episode_rewards
            batch_actions += episode_actions
            batch_states += episode_states
            batch_length += episode_length

            # Output episode rewards
            rewards = np.array(episode_rewards)
            won = len(rewards[rewards == 1])
            lost = len(rewards[rewards == -1])
            print('Episode {}.{}   AI: {} - {} : RL'.format(i_episode, i_batch,
                lost, won))
            batch_results += [[lost, won]]

        print('Average episode length: {}'.format(float(batch_length) /
            batch_size))
        mean_batch_results = np.mean(batch_results, 0)
        print('Average episode score: {}'.format(mean_batch_results))

        win_history.append(mean_batch_results)
        if (i_episode % 10) == 0:
            f = open('rewards.pkl', 'wb')
            pickle.dump(win_history, f)
            f.close()

        # Write W1, W2 to file every 10th batch
        if (i_episode % 10) == 0:
            name = 'weights/W1W2-' + str(i_episode) + '.pkl'
            print('Writing W1, W2 to ' + name)
            f = open(name, 'wb')
            pickle.dump([W1, W2], f)
            f.close()

        if plot:
            ax1.clear()
            ax1.plot(win_history)
            plt.pause(0.0001) 

        if show_state:
            state_to_show = np.reshape(batch_states[30], (80, 80))
            ax1.clear()
            ax1.imshow(state_to_show)
            state_to_show = np.reshape(batch_states[35], (80, 80))
            ax2.clear()
            ax2.imshow(state_to_show)
            state_to_show = np.reshape(batch_states[40], (80, 80))
            ax3.clear()
            ax3.imshow(state_to_show)
            state_to_show = np.reshape(batch_states[45], (80, 80))
            ax4.clear()
            ax4.imshow(state_to_show)
            plt.pause(0.0001)

        # Compute the policy gradient for this trajectory
        print('Computing gradients')
        policy_gradient = compute_policy_gradient(batch_rewards,
                batch_actions, batch_states, W1, W2)

        # Adam
        beta1 = 0.9
        beta2 = 0.999
        adam_eps = 1e-8
        adam_t = i_episode + 1
        adam_eta = 0.001

        # Update W1 with Adam
        g1 = policy_gradient[0]
        m1 = beta1 * m1 + (1-beta1) * g1
        v1 = beta2 * v1 + (1-beta2) * g1**2
        m1hat = m1 / (1-beta1**adam_t)
        v1hat = v1 / (1-beta2**adam_t)
        W1 = W1 + adam_eta * m1hat / (np.sqrt(v1hat) + adam_eps)

        # Update W2 with Adam
        g2 = policy_gradient[1]
        m2 = beta1 * m2 + (1-beta1) * g2
        v2 = beta2 * v2 + (1-beta2) * g2**2
        m2hat = m2 / (1-beta1**adam_t)
        v2hat = v2 / (1-beta2**adam_t)
        W2 = W2 + adam_eta * m2hat / (np.sqrt(v2hat) + adam_eps)

    # Return our trained theta
    return W1, W2

# Initialises weights for a feed forward neural network as described in
# Efficient Backprop
def initialise_weights(num_input, num_output):
    initial_std = 1e-3/np.sqrt(num_input)
    return np.random.randn(num_output, num_input) * initial_std

# observation and theta are both row vectors.
# We want to find theta such that observation . theta > 0 is a good predictor
# for the 'move right' action.
def policy_forward(state, W1, W2):
    # Compute first fully connected layer
    fc1 = np.dot(W1, state)

    # Apply relu
    relu1 = np.copy(fc1)
    relu1[relu1 < 0] = 0
    
    # Compute second fully connected layer
    fc2 = np.dot(W2, relu1)

    # Return the layer outputs
    return [state, fc1, relu1, fc2, sigmoid(fc2)]

# Samples an action from the policy
# observation: an observation from the environment
# theta: the parameter vector theta
# Returns: a sample from the policy distribution. The distribution is: move
# right with probability sigma(x dot theta), and otherwise move left.
def sample_action(state, W1, W2):
    prob_up = policy_forward(state, W1, W2)[-1]
    r = np.random.rand()
    if r < prob_up:
        return MOVE_UP
    else:
        return MOVE_DOWN

# Computes the sigmoid function
# u: a real number
def sigmoid(u):
    u = np.min([u, 500])
    u = np.max([u, -500])
    return 1.0 / (1.0 + np.exp(-u))

# Computes the gradient of pi with respect to W1 and W2. Note that pi is the
# probability of moving up.
def compute_policy_gradient_one_step(state, W1, W2):
    layer_outputs = policy_forward(state, W1, W2)
    state = layer_outputs[0]
    fc1 = layer_outputs[1]
    relu1 = layer_outputs[2]
    fc2 = layer_outputs[3]
    softmax = layer_outputs[4]

    dpi_dfc2 = softmax * (1-softmax)

    dfc2_drelu1 = np.transpose(W2)

    dpi_drelu1 = dpi_dfc2 * dfc2_drelu1

    # We can now compute dpi_dW2
    dfc2_dW2 = np.transpose(relu1)
    dpi_dW2 = dpi_dfc2 * dfc2_dW2

    # Move on to dpi_dW1. First keep backpropagating.
    drelu1_dfc1 = np.ones(np.shape(fc1))
    drelu1_dfc1[fc1 < 0] = 0
    dpi_dfc1 = dpi_drelu1 * drelu1_dfc1

    # The (i,j,k) entry of dfc1_dW1 is d(fc1)_i / d(W1)_jk.
    dfc1_dW1 = np.zeros((np.shape(fc1)[0], np.shape(W1)[0], np.shape(W1)[1]))
    for i in xrange(np.shape(fc1)[0]):
        dfc1_dW1[i,i,:] = np.transpose(state)
    dpi_dW1 = np.tensordot(dpi_dfc1, dfc1_dW1, axes=(0,0))
    dpi_dW1 = np.reshape(dpi_dW1, np.shape(W1))

    return dpi_dW1, dpi_dW2, softmax

# This function computes the gradient of the policy with respect to theta for
# the specified trajectory.
# - episode_rewards: the rewards of the episode
# - episode_actions: the actions of the episode
# - episode_states: the states of the episode
# - W1, W2: the parameters for the policy that ran the episode
def compute_policy_gradient(episode_rewards, episode_actions,
        episode_states, W1, W2):
    # The gradient computation is explained at https://cgnicholls.github.io

    grad_W1_log_pi = np.zeros(np.shape(W1))
    grad_W2_log_pi = np.zeros(np.shape(W2))

    episode_length = len(episode_rewards)

    # Normalizes the positive and negative rewards
    normalized_rewards = normalize_rewards(episode_rewards)
    end_points = [t for t in xrange(len(episode_rewards)) if \
            episode_rewards[t]  != 0]
    normalized_rewards = propagate_reward_for_point(normalized_rewards,
            end_points)

    for t in xrange(episode_length):
        sys.stdout.write('Progress: %d%%   \r' % int(100*float(t+1) / \
                float(episode_length)) )
        sys.stdout.flush()
        state = episode_states[t]
        grad_W1, grad_W2, policy = compute_policy_gradient_one_step(state, W1,
                W2)
        
        # Above, we've computed the gradient for going up. But if we actually
        # went down on this action, then we should compute grad log (1-pi),
        # which is (grad (1-pi)) / (1-pi) = -(grad pi) / (1-pi).
        if episode_actions[t] == MOVE_DOWN:
            grad_W1 = -grad_W1
            grad_W2 = -grad_W2
            policy = 1-policy

        # Set the reward for time t as the next nonzero reward. This is the
        # reward for the current point, i.e. until one person misses the ball.
        #reward = reward_for_this_point(episode_rewards[t::])
        reward = normalized_rewards[t]

        #discount = 0.9
        #reward = discounted_reward(episode_rewards[t::], discount)

        # Update the gradients by this reward
        grad_W1_log_pi += grad_W1 / (1e-8 + policy) * reward
        grad_W2_log_pi += grad_W2 / (1e-8 + policy) * reward
    return grad_W1_log_pi / episode_length, grad_W2_log_pi / episode_length

# Given rewards for all timesteps in pong, transform them to have mean zero and
# standard deviation one.
def normalize_rewards(rewards):
    rewards = np.array(rewards)
    rewards[rewards!=0] -= np.mean(rewards[rewards!=0])
    #std = np.std(rewards[rewards!=0])
    #if std != np.nan:
    #    rewards[rewards!=0] /= np.std(rewards[rewards!=0])
    return rewards
    
# Given end points for each point, copy the reward for the point back to all
# timesteps in the point
def propagate_reward_for_point(rewards, end_points):
    i_end_point = 0
    for i in xrange(len(rewards)):
        # If no more end points, then return
        if i_end_point >= len(end_points):
            return rewards
        # If we have not reached the end of the point, set the reward as the
        # reward for the point
        if i <= end_points[i_end_point]:
            rewards[i] = rewards[end_points[i_end_point]]
        # Otherwise, we increment the end point
        else:
            i_end_point += 1
    return rewards

def discounted_reward(rewards, discount):
    reward = 0
    for i in xrange(len(rewards)):
        reward += rewards[i] * discount
        discount *= discount
    return reward

# Takes a sequence of rewards for each time step, and computes the reward for
# the current point. This is then next nonzero element, if it exists, and
# otherwise zero.
def reward_for_this_point(rewards):
    for i in xrange(len(rewards)):
        if rewards[i] != 0:
            if rewards[i] == 1:
                return 1
            else:
                return -1
    return 0

# Run an episode with the policy parametrised by theta.
# - theta: the parameter to use for the policy
# - max_episode_length: the maximum length of an episode
# - render: whether or not to show the episode
# Returns the episode rewards, episode actions and episode observations
def run_episode(W1, W2, max_episode_length, render=False):
    # Reset the environment
    observation = env.reset()
    episode_rewards = []
    episode_actions = []
    episode_observations = []
    episode_states = []
    
    prev_obs = None
    for t in xrange(max_episode_length):
        episode_observations.append(observation)
        # If rendering, draw the environment
        if render:
            env.render()

        # Set up the state
        state = compute_state(observation, prev_obs)
        episode_states.append(state)
        prev_obs = observation

        a_t = sample_action(state, W1, W2)
        episode_actions.append(a_t)
        observation, reward, done, info = env.step(a_t)
        episode_rewards.append(reward)
        if done:
            break
    episode_length = t+1
    return episode_rewards, episode_actions, episode_states, episode_length

# Apply preprocessing to remove the game border, and downsample the frame. Also
# zero out the background, and 
def preprocessing(obs):
    # Just keep the game screen -- not the score etc.
    # We also only need one colour channel
    obs = obs[35:194,:,0]

    # Downsample the observation
    obs = obs[::2,::2]

    # Erase background
    obs[obs == 144] = 0
    obs[obs == 109] = 0

    # Set everything else to 1
    obs[obs != 0] = 1

    # Return as a column vector
    obs = np.reshape(obs, (-1, 1))
    return obs

# Pass in the current and previous observations. If the previous observation
# observation. If the previous observation is given, then return curr_obs -
# prev_obs. If not, then return all zeroes.
def compute_state(curr_obs, prev_obs):
    if prev_obs is not None:
        state = preprocessing(curr_obs) - preprocessing(prev_obs)
    else:
        state = np.zeros(np.shape(preprocessing(curr_obs)))
    return state

def numerical_gradient(state, W1, W2, eps):
    state = np.reshape(state, (-1, 1))
    grad_W1 = np.zeros(np.shape(W1))
    for i in xrange(np.shape(W1)[0]):
        for j in xrange(np.shape(W1)[1]):
            W1_plus = np.copy(W1)
            W1_plus[i,j] += eps
            W1_minus = np.copy(W1)
            W1_minus[i,j] -= eps
            grad_W1[i,j] = (policy_forward(state, W1_plus, W2)[-1] -
                    policy_forward(state, W1_minus, W2)[-1]) / (2*eps)

    grad_W2 = np.zeros(np.shape(W2))
    for i in xrange(np.shape(W2)[0]):
        for j in xrange(np.shape(W2)[1]):
            W2_plus = np.copy(W2)
            W2_plus[i,j] += eps
            W2_minus = np.copy(W2)
            W2_minus[i,j] -= eps
            grad_W2[i,j] = (policy_forward(state, W1, W2_plus)[-1] -
                    policy_forward(state, W1, W2_minus)[-1]) / (2*eps)

    return grad_W1, grad_W2

# Test gradients
def test_gradient_specific(eps, state, W1, W2):
    grad_W1_num, grad_W2_num = numerical_gradient(state, W1, W2, eps)
    grad_W1_an, grad_W2_an, _ = compute_policy_gradient_one_step(state, W1, W2)

    relative_error_W1 = relative_error(grad_W1_num, grad_W1_an, eps)
    relative_error_W2 = relative_error(grad_W2_num, grad_W2_an, eps)
    return [relative_error_W1, relative_error_W2]

def test_gradient(eps, num_input=100, num_hidden=6, num_tests=10):
    max_relative_error_W1 = 0
    max_relative_error_W2 = 0

    for i in xrange(num_tests):
        state = np.random.randn(num_input, 1)
        W1 = np.random.randn(num_hidden, num_input) * 0.1
        W2 = np.random.randn(1, num_hidden) * 0.1
        [relative_error_W1, relative_error_W2] = test_gradient_specific(eps, state,
                W1, W2)
        max_relative_error_W1 = np.max([max_relative_error_W1,
            relative_error_W1])
        max_relative_error_W2 = np.max([max_relative_error_W2,
            relative_error_W2])
    return [max_relative_error_W1, max_relative_error_W2]

def relative_error(arr1, arr2, eps):
    abs_error = np.sum(np.abs(np.reshape(arr1 - arr2, (1,-1))))
    norm1 = np.sum(np.abs(np.reshape(arr1, (1,-1))))
    norm2 = np.sum(np.abs(np.reshape(arr2, (1,-1))))
    return abs_error / min(1e-20 + norm1, 1e-20 + norm2)

if __name__ == '__main__':
    # Test the gradients numerically
    print('Testing gradients')
    [max_relative_error_W1, max_relative_error_W2] = test_gradient(1e-6)
    print('Max rel error W1 {}'.format(max_relative_error_W1))
    print('Max rel error W2 {}'.format(max_relative_error_W2))

    # Train the agent
    num_episodes = 100000
    max_episode_length = 2000
    W1, W2 = train_policy_gradient_agent(num_episodes, max_episode_length,
                                         batch_size=2, num_hidden=5, render=False)
    
    # Run the agent for 10 episodes
    policy_gradient_agent(10, W1, W2, max_episode_length)
