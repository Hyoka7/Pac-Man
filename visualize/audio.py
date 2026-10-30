from enum import Enum, auto

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
        if self.current_state == AudioState.MENU:
            return
        pygame.mixer.music.load("assets/audio/menu_bgm.mp3")
        pygame.mixer.music.play(-1)
        self.current_state = AudioState.MENU

    def play_playing_bgm(self) -> None:
        if self.current_state == AudioState.PLAYING:
            return
        pygame.mixer.music.load("assets/audio/playing.ogg")
        pygame.mixer.music.play(-1)
        self.current_state = AudioState.PLAYING

    def play_gameover_bgm(self) -> None:
        if self.current_state == AudioState.GAMEOVER:
            return
        pygame.mixer.music.load("assets/audio/gameover.mp3")
        pygame.mixer.music.play(-1)
        self.current_state = AudioState.GAMEOVER

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
