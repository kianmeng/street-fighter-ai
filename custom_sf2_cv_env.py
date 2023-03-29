import gym
import cv2
import numpy as np
import torch
from torchvision.transforms import Normalize
from gym.spaces import MultiBinary

# Custom environment wrapper
class StreetFighterCustomWrapper(gym.Wrapper):
    def __init__(self, env, win_template, lose_template, testing=False, threshold=0.65):
        super(StreetFighterCustomWrapper, self).__init__(env)
        self.action_space = MultiBinary(12)
        
        # self.win_template = win_template
        # self.lose_template = lose_template
        self.threshold = threshold
        self.game_screen_gray = None

        self.prev_player_health = 1.0
        self.prev_opponent_health = 1.0

        # Update observation space to single-channel grayscale image
        # self.observation_space = gym.spaces.Box(
        #     low=0.0, high=1.0, shape=(84, 84, 1), dtype=np.float32
        # )

        # observation_space for mobilenet
        self.observation_space = gym.spaces.Box(
            low=0.0, high=1.0, shape=(3, 96, 96), dtype=np.float32
        )

        self.testing = testing

        # Normalize the image for MobileNetV3Small.
        self.normalize = Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    
    def _preprocess_observation(self, observation):
        # self.game_screen_gray = cv2.cvtColor(observation, cv2.COLOR_BGR2GRAY)
        # resized_image = cv2.resize(self.game_screen_gray, (84, 84), interpolation=cv2.INTER_AREA) / 255.0
        # return np.expand_dims(resized_image, axis=-1)
        
        # # Using MobileNetV3Small.
        self.game_screen_gray = cv2.cvtColor(observation, cv2.COLOR_BGR2GRAY)
        resized_image = cv2.resize(observation, (96, 96), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        
        # Convert the NumPy array to a PyTorch tensor
        resized_image = torch.from_numpy(resized_image).permute(2, 0, 1)

        # Apply normalization
        resized_image = self.normalize(resized_image)

        # # Add a batch dimension to match the model input shape
        # # resized_image = resized_image.unsqueeze(0)
        return resized_image

    def _get_win_or_lose_bonus(self):
        if self.prev_player_health > self.prev_opponent_health:
            # print('You win!')
            return 300
        else:
            # print('You lose!')
            return -300
        
    def _get_reward(self):
        player_health_area = self.game_screen_gray[15:20, 32:120]
        oppoent_health_area = self.game_screen_gray[15:20, 136:224]
        
        # Get health points using the number of pixels above 129.
        player_health = np.sum(player_health_area > 129) / player_health_area.size
        opponent_health = np.sum(oppoent_health_area > 129) / oppoent_health_area.size

        player_health_diff = self.prev_player_health - player_health
        opponent_health_diff = self.prev_opponent_health - opponent_health

        reward = (opponent_health_diff - player_health_diff) * 200 # max would be 200

        # Penalty for each step without any change in health
        if opponent_health_diff <= 0.0000001:
            reward -= 12.0 / 60.0 # -12 points per second if no damage to opponent

        self.prev_player_health = player_health
        self.prev_opponent_health = opponent_health

        # Print the health values of the player and the opponent
        # print("Player health: %f Opponent health:%f" % (player_health, opponent_health))
        return reward

    def reset(self):
        observation = self.env.reset()
        self.prev_player_health = 1.0
        self.prev_opponent_health = 1.0
        return self._preprocess_observation(observation)

    def step(self, action):
        # observation, _, _, info = self.env.step(action)
        observation, _reward, _done, info = self.env.step(self.env.action_space.sample())
        custom_reward = self._get_reward()
        custom_reward -= 1.0 / 60.0 # penalty for each step (-1 points per second)

        custom_done = False
        if self.prev_player_health <= 0.00001 or self.prev_opponent_health <= 0.00001:
            custom_reward += self._get_win_or_lose_bonus()
            if not self.testing:
                custom_done = True
            else:
                self.prev_player_health = 1.0
                self.prev_opponent_health = 1.0
             
        return self._preprocess_observation(observation), custom_reward, custom_done, info
    