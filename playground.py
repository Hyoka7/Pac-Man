"""Standalone Pillow text preview; the game uses visualize.image_renderer.ImageRenderer."""

import pygame

if __name__ == "__main__":
    pygame.mixer.init()
    pygame.mixer.music.load("assets/audio/menu_bgm.mp3")
    pygame.mixer.music.play(-1)
    input()
    pygame.mixer.quit()