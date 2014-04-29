#
# PC-BASIC 3.23 - nosound.py
#
# Null sound implementation
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import event_loop
import datetime

music_foreground = True
music_queue = []

def music_queue_length():
    # top of sound_queue is currently playing
    return max(0, len(music_queue)-1)
    
def beep():
    play_sound(800, 0.25)
    
def init_sound():
    return True
    
def stop_all_sound():
    global music_queue
    music_queue = []
    
def play_sound(frequency, duration, fill=1, loop=False):
    if music_queue:
        latest = max(music_queue)
    else:    
        latest = datetime.datetime.now()
    wait_music(15)    
    music_queue.append(latest + datetime.timedelta(seconds=duration))
        
def check_sound():
    now = datetime.datetime.now()
    while music_queue and now >= music_queue[0]:
        music_queue.pop(0)
    
def wait_music(wait_length=0, wait_last=True):
    while len(music_queue) + wait_last - 1 > wait_length:
        event_loop.idle()
        event_loop.check_events()
        check_sound()
      
