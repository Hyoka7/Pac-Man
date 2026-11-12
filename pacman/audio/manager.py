"""Background music and sound effects; silently disabled without audio."""

import sys
from enum import Enum, auto
from pathlib import Path

import pygame

AUDIO_DIR = Path(__file__).resolve().parents[2] / "assets" / "audio"
"""Audio assets, resolved independently of the working directory."""


class AudioState(Enum):
    """Background track currently selected by AudioManager."""

    MENU = auto()
    PLAYING = auto()
    GAMEOVER = auto()


class AudioManager:
    """Play game audio, or do nothing when the device or files are missing."""

    def __init__(self) -> None:
        """Start the mixer and load sound effects, or disable audio."""
        self.current_state: AudioState | None = None
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
            self.enabled = True
            for name in ("pacgum", "eat", "powerup"):
                self.sounds[name] = pygame.mixer.Sound(
                    str(AUDIO_DIR / f"{name}.mp3")
                )
        except (pygame.error, OSError) as err:
            self._disable(err)

    def _disable(self, err: Exception) -> None:
        """Turn audio off for the rest of the session after a failure.

        Args:
            err: Error that caused audio to be disabled.
        """
        print(f"Warning: audio disabled: {err}", file=sys.stderr)
        if self.enabled:
            pygame.mixer.quit()
        self.enabled = False
        self.sounds.clear()
        self.current_state = None

    def play_menu_bgm(self) -> None:
        """Loop the menu music unless it is already playing."""
        self._play_bgm(AudioState.MENU, "menu_bgm.mp3")

    def play_playing_bgm(self) -> None:
        """Loop the gameplay music unless it is already playing."""
        self._play_bgm(AudioState.PLAYING, "playing.ogg")

    def play_gameover_bgm(self) -> None:
        """Loop the game-over music unless it is already playing."""
        self._play_bgm(AudioState.GAMEOVER, "gameover.mp3")

    def _play_bgm(self, state: AudioState, filename: str) -> None:
        """Switch the looping background track.

        Args:
            state: Track identifier used to skip reloading the same music.
            filename: File name inside the audio asset directory.
        """
        if not self.enabled or self.current_state == state:
            return
        try:
            pygame.mixer.music.load(str(AUDIO_DIR / filename))
            pygame.mixer.music.play(-1)
        except (pygame.error, OSError) as err:
            self._disable(err)
            return
        self.current_state = state

    def _play_sound(self, name: str) -> None:
        """Play a loaded sound effect by name, if audio is enabled.

        Args:
            name: Key of the effect in ``self.sounds``.
        """
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def pacgum_sound(self) -> None:
        """Play the effect for eating a normal pacgum."""
        self._play_sound("pacgum")

    def super_pacgum_sound(self) -> None:
        """Play the effect for eating a super pacgum."""
        self._play_sound("powerup")

    def eating_sound(self) -> None:
        """Play the effect for eating a ghost."""
        self._play_sound("eat")

    def stop_bgm(self) -> None:
        """Stop the background track while keeping the mixer open."""
        if not self.enabled or self.current_state is None:
            return
        pygame.mixer.music.stop()
        self.current_state = None

    def close(self) -> None:
        """Shut down the mixer once audio is no longer needed."""
        if self.enabled:
            pygame.mixer.quit()
            self.enabled = False
