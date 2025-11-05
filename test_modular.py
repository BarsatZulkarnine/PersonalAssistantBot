import pygame, time
pygame.mixer.init()
pygame.mixer.music.load("C:\\Users\\msi\\Music\\Hope.mp3")
pygame.mixer.music.set_volume(1.0)
pygame.mixer.music.play()
print("Playing…", pygame.mixer.music.get_busy())
while pygame.mixer.music.get_busy():
    time.sleep(1)
