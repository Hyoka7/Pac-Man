import os
from enum import Enum, auto

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame


class AudioState(Enum):
    MENU = auto()
    PLAYING = auto()
    GAMEOVER = auto()

class AudioManager:
    def __init__(self) -> None:
        pygame.mixer.init()
        self.current_state: AudioState | None = None
        # Sound.set_volume(0.0 - 1.0)
        self.coin_sound = pygame.mixer.Sound("assets/audio/pacgum.mp3")
        self.eat_sound = pygame.mixer.Sound("assets/audio/eat.mp3")
        self.power_up_sound = pygame.mixer.Sound("assets/audio/powerup.mp3")

    def play_menu_bgm(self) -> None:
        self._play_bgm(AudioState.MENU, "assets/audio/menu_bgm.mp3")

    def play_playing_bgm(self) -> None:
        self._play_bgm(AudioState.PLAYING, "assets/audio/playing.ogg")

    def play_gameover_bgm(self) -> None:
        self._play_bgm(AudioState.GAMEOVER, "assets/audio/gameover.mp3")

    def _play_bgm(self, state: AudioState, filename: str) -> None:
        if self.current_state == state:
            return
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play(-1)
        self.current_state = state

    def pacgum_sound(self) -> None:
        self.coin_sound.play()

    def super_pacgum_sound(self) -> None:
        self.power_up_sound.play()

    def eating_sound(self) -> None:
        self.eat_sound.play()

    def stop_bgm(self) -> None:
        if self.current_state is None:
            return
        pygame.mixer.music.stop()
        self.current_state = None

    def close(self) -> None:
        pygame.mixer.quit()
