import speake3
import pygame

class SoundInterface():
    
    def __init__(self):
        self.engine = speake3.Speake()
        self.engine.set('voice', 'en-scotish')
        self.engine.set('speed', '150')
        self.engine.set('pitch', '60')
        #load music player
        pygame.mixer.init()
        self.load.mp3("stayingalive.mp3")
        return
    
    def load_mp3(self, song):
        pygame.mixer.music.load(song)
        return
    
    def get_all_voices(self):
        voices = self.engine.get("voices")
        for voice in voices:
            print(voice)
        voices_2 = self.engine.get("voices", "en")
        for voice in voices_2:
            print(voice)
        return
    
    def say(self, message):
        self.engine.say(message)
        self.engine.talkback()
        return
    
    def play_music(self):
        pygame.mixer.music.play()
        return
    
    def pause_music(self):
        pygame.mixer.music.pause()
        return
    
    def unpause_music(self):
        pygame.mixer.music.unpause()
        

#---------------------------------------------
#only execute if this is the main file, good for testing code.
        
if name == "__main__":
    sound.SoundInterface()
    sound.play_music()
    sound.say("I am here to save you fool. Why you so dumb to get stuck in a fire in the first place")
    
    
    
    