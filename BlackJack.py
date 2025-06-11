import os
from typing import Optional
import numpy as np
import gym
from gym import spaces
from gym.error import DependencyNotInstalled


def cmp(a, b):
    return float(a > b) - float(a < b)


deck = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]


def draw_card(np_random):
    return int(np_random.choice(deck))


def draw_hand(np_random):
    return [draw_card(np_random), draw_card(np_random)]


def usable_ace(hand):
    return 1 in hand and sum(hand) + 10 <= 21


def sum_hand(hand):
    if usable_ace(hand):
        return sum(hand) + 10
    return sum(hand)


def is_bust(hand):
    return sum_hand(hand) > 21


def score(hand):
    return 0 if is_bust(hand) else sum_hand(hand)


def is_natural(hand):
    return sorted(hand) == [1, 10]


class BlackjackEnv(gym.Env):
    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_fps": 4,
    }

    def __init__(self, render_mode: Optional[str] = None, natural=False, sab=False):
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Tuple(
            (spaces.Discrete(32), spaces.Discrete(11), spaces.Discrete(2))
        )

        self.natural = natural
        self.sab = sab
        self.render_mode = render_mode
        self.result_message = None
        self.should_quit = False
        # Define screen dimensions as class variables
        self.screen_width = 600
        self.screen_height = 500

    def step(self, action):
        assert self.action_space.contains(action)
        if action:  # hit
            self.player.append(draw_card(self.np_random))
            if is_bust(self.player):
                terminated = True
                reward = -1.0
                self.result_message = "You Lose!"
            else:
                terminated = False
                reward = 0.0
                self.result_message = None
        else:  # stick
            terminated = True
            while sum_hand(self.dealer) < 17:
                self.dealer.append(draw_card(self.np_random))
            reward = cmp(score(self.player), score(self.dealer))
            if self.sab and is_natural(self.player) and not is_natural(self.dealer):
                reward = 1.0
            elif (
                    not self.sab
                    and self.natural
                    and is_natural(self.player)
                    and reward == 1.0
            ):
                reward = 1.5
            if reward > 0:
                self.result_message = "You Win!"
            elif reward < 0:
                self.result_message = "You Lose!"
            else:
                self.result_message = "Draw!"

        if self.render_mode == "human":
            self.render()
        return self._get_obs(), reward, terminated, False, {}

    def _get_obs(self):
        return (sum_hand(self.player), self.dealer[0], usable_ace(self.player))

    def reset(
            self,
            seed: Optional[int] = None,
            options: Optional[dict] = None,
    ):
        super().reset(seed=seed)
        self.dealer = draw_hand(self.np_random)
        self.player = draw_hand(self.np_random)
        self.result_message = None

        _, dealer_card_value, _ = self._get_obs()

        suits = ["C", "D", "H", "S"]
        self.dealer_top_card_suit = self.np_random.choice(suits)

        if dealer_card_value == 1:
            self.dealer_top_card_value_str = "A"
        elif dealer_card_value == 10:
            self.dealer_top_card_value_str = self.np_random.choice(["J", "Q", "K"])
        else:
            self.dealer_top_card_value_str = str(dealer_card_value)

        if self.render_mode == "human":
            self.render()
        return self._get_obs(), {}

    def render(self):
        if self.render_mode is None:
            gym.logger.warn("You are calling render method without specifying any render mode.")
            return

        try:
            import pygame
        except ImportError:
            raise DependencyNotInstalled("pygame is not installed, run `pip install gym[toy_text]`")

        player_sum, dealer_card_value, usable_ace = self._get_obs()
        card_img_height = self.screen_height // 3
        card_img_width = int(card_img_height * 142 / 197)
        spacing = self.screen_height // 20

        white = (255, 255, 255)
        black = (0, 0, 0)
        shadow_color = (50, 50, 50)
        border_color = (139, 69, 19)
        win_color = (0, 255, 0)
        lose_color = (255, 0, 0)
        draw_color = (255, 255, 0)

        if not hasattr(self, "screen"):
            pygame.init()
            if self.render_mode == "human":
                pygame.display.init()
                pygame.display.set_caption("Blackjack")
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            else:
                pygame.font.init()
                self.screen = pygame.Surface((self.screen_width, self.screen_height))

        if not hasattr(self, "clock"):
            self.clock = pygame.time.Clock()

        if not hasattr(self, "table_background"):
            table_path = os.path.join(os.path.dirname(__file__), "table.png")
            try:
                table_img = pygame.image.load(table_path)
                self.table_background = pygame.transform.scale(table_img, (self.screen_width, self.screen_height))
            except pygame.error:
                self.table_background = pygame.Surface((self.screen_width, self.screen_height))
                for y in range(self.screen_height):
                    for x in range(self.screen_width):
                        noise = np.random.randint(-10, 10)
                        r = max(0, min(255, 7 + noise))
                        g = max(0, min(255, 99 + noise))
                        b = max(0, min(255, 36 + noise))
                        self.table_background.set_at((x, y), (r, g, b))

        self.screen.blit(self.table_background, (0, 0))
        pygame.draw.rect(self.screen, border_color, (0, 0, self.screen_width, self.screen_height), 10)

        def get_image(path):
            cwd = os.path.dirname(__file__)
            full_path = os.path.join(cwd, path)
            try:
                image = pygame.image.load(full_path)
            except pygame.error:
                image = pygame.Surface((card_img_width, card_img_height))
                image.fill((100, 100, 100))
            return image

        def get_font(path, size):
            cwd = os.path.dirname(__file__)
            try:
                font = pygame.font.Font(os.path.join(cwd, path), size)
            except pygame.error:
                font = pygame.font.SysFont("arial", size)
            return font

        small_font = get_font(os.path.join("font", "MyWorking.otf"), self.screen_height // 15)
        large_font = get_font(os.path.join("font", "MyWorking.otf"), self.screen_height // 6)
        title_font = get_font(os.path.join("font", "MyWorking.otf"), self.screen_height // 10)

        title_text = title_font.render("Blackjack", True, white)
        title_shadow = title_font.render("Blackjack", True, shadow_color)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, spacing))
        self.screen.blit(title_shadow, title_rect.move(2, 2))
        self.screen.blit(title_text, title_rect)

        dealer_text = small_font.render("Dealer: " + str(dealer_card_value), True, white)
        dealer_text_shadow = small_font.render("Dealer: " + str(dealer_card_value), True, shadow_color)
        dealer_text_rect = dealer_text.get_rect(topleft=(spacing, title_rect.bottom + spacing))
        self.screen.blit(dealer_text_shadow, dealer_text_rect.move(2, 2))
        self.screen.blit(dealer_text, dealer_text_rect)

        def scale_card_img(card_img):
            return pygame.transform.scale(card_img, (card_img_width, card_img_height))

        value_map = {
            "A": "ace", "J": "jack", "Q": "queen", "K": "king",
            "1": "1", "2": "2", "3": "3", "4": "4", "5": "5",
            "6": "6", "7": "7", "8": "8", "9": "9", "10": "10"
        }
        suit_map = {
            "C": "clubs", "D": "diamonds", "H": "hearts", "S": "spades"
        }

        card_value = value_map.get(self.dealer_top_card_value_str, self.dealer_top_card_value_str)
        card_suit = suit_map.get(self.dealer_top_card_suit, self.dealer_top_card_suit)
        card_filename = f"{card_value}_of_{card_suit}.png"

        card_path = os.path.join("Playing Cards", card_filename)
        dealer_card_img = scale_card_img(get_image(card_path))
        dealer_card_rect = dealer_card_img.get_rect(
            topleft=(self.screen_width // 2 - card_img_width - spacing // 2, dealer_text_rect.bottom + spacing)
        )
        shadow_rect = dealer_card_rect.move(5, 5)
        pygame.draw.rect(self.screen, shadow_color, shadow_rect, border_radius=5)
        pygame.draw.rect(self.screen, white, dealer_card_rect.inflate(4, 4), 2)
        self.screen.blit(dealer_card_img, dealer_card_rect)

        hidden_card_path = os.path.join("Playing Cards", "Card.png")
        hidden_card_img = scale_card_img(get_image(hidden_card_path))
        hidden_card_img = pygame.transform.rotate(hidden_card_img, 5)
        hidden_card_rect = hidden_card_img.get_rect(
            topleft=(self.screen_width // 2 + spacing // 2, dealer_text_rect.bottom + spacing)
        )
        shadow_rect = hidden_card_rect.move(5, 5)
        pygame.draw.rect(self.screen, shadow_color, shadow_rect, border_radius=5)
        pygame.draw.rect(self.screen, white, hidden_card_rect.inflate(4, 4), 2)
        self.screen.blit(hidden_card_img, hidden_card_rect)

        player_text = small_font.render("Player", True, white)
        player_text_shadow = small_font.render("Player", True, shadow_color)
        player_text_rect = player_text.get_rect(topleft=(spacing, hidden_card_rect.bottom + 1.5 * spacing))
        self.screen.blit(player_text_shadow, player_text_rect.move(2, 2))
        self.screen.blit(player_text, player_text_rect)

        player_sum_text = large_font.render(str(player_sum), True, white)
        player_sum_shadow = large_font.render(str(player_sum), True, shadow_color)
        player_sum_rect = player_sum_text.get_rect(
            center=(self.screen_width // 2, player_text_rect.bottom + spacing + player_sum_text.get_height() // 2)
        )
        self.screen.blit(player_sum_shadow, player_sum_rect.move(2, 2))
        self.screen.blit(player_sum_text, player_sum_rect)

        if usable_ace:
            usable_ace_text = small_font.render("usable ace", True, white)
            usable_ace_shadow = small_font.render("usable ace", True, shadow_color)
            usable_ace_rect = usable_ace_text.get_rect(
                center=(
                self.screen_width // 2, player_sum_rect.bottom + spacing // 2 + usable_ace_text.get_height() // 2)
            )
            self.screen.blit(usable_ace_shadow, usable_ace_rect.move(2, 2))
            self.screen.blit(usable_ace_text, usable_ace_rect)

        if self.result_message:
            result_color = win_color if "Win" in self.result_message else lose_color if "Lose" in self.result_message else draw_color
            result_text = large_font.render(self.result_message, True, result_color)
            result_shadow = large_font.render(self.result_message, True, shadow_color)
            result_rect = result_text.get_rect(
                center=(self.screen_width // 2, self.screen_height - spacing - result_text.get_height()))
            background_rect = result_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (0, 0, 0, 128), background_rect, border_radius=5)
            self.screen.blit(result_shadow, result_rect.move(2, 2))
            self.screen.blit(result_text, result_rect)

        if self.render_mode == "human":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.should_quit = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.should_quit = True

            pygame.display.update()
            self.clock.tick(self.metadata["render_fps"])
        else:
            return np.transpose(np.array(pygame.surfarray.pixels3d(self.screen)), axes=(1, 0, 2))

    def close(self):
        if hasattr(self, "screen"):
            import pygame
            pygame.display.quit()
            pygame.quit()


def main():
    env = BlackjackEnv(render_mode="human", natural=True, sab=False)

    num_episodes = 3
    for episode in range(num_episodes):
        if env.should_quit:
            break

        print(f"\nEpisode {episode + 1}")
        obs, info = env.reset()
        print(f"Initial Observation: Player Sum = {obs[0]}, Dealer Card = {obs[1]}, Usable Ace = {bool(obs[2])}")

        done = False
        while not done and not env.should_quit:
            action = 1 if obs[0] < 17 else 0
            action_str = "Hit" if action == 1 else "Stick"
            print(f"Action: {action_str}")

            obs, reward, terminated, truncated, info = env.step(action)
            print(
                f"Observation: Player Sum = {obs[0]}, Dealer Card = {obs[1]}, Usable Ace = {bool(obs[2])}, Reward = {reward}")

            done = terminated or truncated
            if env.render_mode == "human":
                import pygame
                pygame.time.wait(1000)

        if env.should_quit:
            break

        if reward > 0:
            print("Result: Player Wins!")
        elif reward < 0:
            print("Result: Dealer Wins!")
        else:
            print("Result: Draw!")
        print(f"Episode finished with reward: {reward}")

        if env.render_mode == "human":
            pygame.time.wait(2000)

    if env.render_mode == "human" and not env.should_quit:
        large_font = pygame.font.Font(os.path.join(os.path.dirname(__file__), "font", "MyWorking.otf"),
                                      env.screen_height // 6)
        game_over_text = large_font.render("Game Over!", True, (255, 255, 255))
        game_over_shadow = large_font.render("Game Over!", True, (50, 50, 50))
        game_over_rect = game_over_text.get_rect(center=(env.screen_width // 2, env.screen_height // 2))
        background_rect = game_over_rect.inflate(20, 10)
        env.screen.blit(env.table_background, (0, 0))
        pygame.draw.rect(env.screen, (0, 0, 0, 128), background_rect, border_radius=5)
        env.screen.blit(game_over_shadow, game_over_rect.move(2, 2))
        env.screen.blit(game_over_text, game_over_rect)
        pygame.display.update()
        pygame.time.wait(3000)

    env.close()


if __name__ == "__main__":
    main()