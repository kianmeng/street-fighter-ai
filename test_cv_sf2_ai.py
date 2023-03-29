import time 

import cv2
import torch
import gym
import retro
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from custom_cnn import CustomCNN
from mobilenet_extractor import MobileNetV3Extractor
from custom_sf2_cv_env import StreetFighterCustomWrapper
    
def make_env(game, state, seed=0):
    def _init():
        win_template = cv2.imread('images/pattern_win_gray.png', cv2.IMREAD_GRAYSCALE)
        lose_template = cv2.imread('images/pattern_lose_gray.png', cv2.IMREAD_GRAYSCALE)
        env = retro.RetroEnv(
            game=game, 
            state=state, 
            use_restricted_actions=retro.Actions.FILTERED, 
            obs_type=retro.Observations.IMAGE    
        )
        env = StreetFighterCustomWrapper(env, win_template, lose_template, testing=True)
        # env.seed(seed)
        return env
    return _init

game = "StreetFighterIISpecialChampionEdition-Genesis"
state_stages = [
    "Champion.Level1.ChunLiVsGuile",
    "Champion.Level2.ChunLiVsKen",
    "Champion.Level3.ChunLiVsChunLi",
    "Champion.Level4.ChunLiVsZangief",
    "Champion.Level5.ChunLiVsDhalsim",
    "Champion.Level6.ChunLiVsRyu",
    "Champion.Level7.ChunLiVsEHonda",
    "Champion.Level8.ChunLiVsBlanka",
    "Champion.Level9.ChunLiVsBalrog",
    "Champion.Level10.ChunLiVsVega",
    "Champion.Level11.ChunLiVsSagat",
    "Champion.Level12.ChunLiVsBison"
    # Add other stages as necessary
]

env = make_env(game, state_stages[0])()

# Wrap the environment
env = DummyVecEnv([lambda: env])

# policy_kwargs = {
#     'features_extractor_class': CustomCNN
# }

# Using MobileNetV3 as the feature extractor
policy_kwargs = {
    'features_extractor_class': MobileNetV3Extractor
}

model = PPO(
    "CnnPolicy", 
    env,
    device="cuda", 
    policy_kwargs=policy_kwargs, 
    verbose=1
)
model.load(r"trained_models_cv_mobilenet_time_penalty/ppo_chunli_1296000_steps")

obs = env.reset()
done = False

while True:
    timestamp = time.time()
    action, _ = model.predict(obs)
    obs, rewards, done, info = env.step(action)
    env.render()
    render_time = time.time() - timestamp
    if render_time < 0.0111:
        time.sleep(0.0111 - render_time)  # Add a delay for 90 FPS

# env.close()
