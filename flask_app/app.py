from flask import Flask, render_template, send_file, send_from_directory
from main.music_model import Bar, main
from shutil import copyfile, copy
import os
import re
import requests
import threading


app = Flask(__name__)
audio_names = []
number_produced = 0

@app.route('/')
def hello():
    return render_template('hello.html', next=next)
    

@app.route('/music/create/<n>', methods=['GET'])
def create_bar():
    """Generates new bar to be played"""

    global audio_names
    global number_produced

    if len(audio_names) < 10:
        temp_fn = f'temp/output_{number_produced}.wav'
        main(1, temp_fn)
        
        new = re.sub('temp', 'static', temp_fn)

        copy(fn, new)
        audio_names.append(new)
        number_produced += 1

    audio_names = list(map(lambda x: re.sub('temp', 'static', x), audio_names))
        
    return ''


def populate_queue():
    """
    Function to update queue after audio returned.
    Triggered by new thread
    """

    l = 10 - len(audio_names)
    for i in range(l):
        create_bar()


def get_audio():
    """Retrieves most recent audio file and returns it"""
    global audio_names
    print(audio_names)
    fn = audio_names.pop(0)
    print(fn)

    return send_file(fn)


@app.route('/music/next')
def next():
    """Returns new audio file from queue after HTML player finishes a file.
    If queue empty, writes new music, then returns it.
    """

    global audio_names

    if len(audio_names) > 0:
        outp = get_audio()
        
    else:
        create_bar()
        outp = get_audio()
    
    # Repopulate Queue while audio plays
    threading.Thread(target=populate_queue).start()
    
    return outp
    
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    Sourced from https://stackoverflow.com/questions/34066804/disabling-caching-in-flask
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'

    return r


if __name__ == '__main__':
    app.run()
