from flask import Flask, render_template, send_file, send_from_directory
from main.music_model import Bar, main
from shutil import copyfile, copy
import os
import re
import requests


app = Flask(__name__)
audio_names = []

@app.route('/')
def hello():
    return render_template('hello.html', next=next)
    

@app.route('/music/create/<n>', methods=['GET'])
def create_bar(n):
    """Generates new bar to be played"""

    global audio_names
    n = int(n)
    if len(audio_names) < 10:
        main(n, 'temp/output')

        for i in range(n):
            fn = f"temp/output_{i}.wav"
            new = re.sub('temp', 'static', fn)

            copy(fn, new)
            audio_names.append(new)

        audio_names = list(map(lambda x: re.sub('temp', 'static', x), audio_names))
        
        return ''


def get_audio():
    """Retrieves most recent audio file and returns it"""
    global audio_names
    print(audio_names)
    fn = audio_names.pop(0)
    print(fn)

    

    return send_file(fn)


@app.route('/music/next')
def next():
    global audio_names

    if len(audio_names) > 0:
        outp = get_audio()
        
    else:
        create_bar(1)
        outp = get_audio()
    
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

    @r.call_on_close
    def repopulate_queue():
        while len(audio_names) < 10:
            create_bar(1)
            
    return r


if __name__ == '__main__':
    app.run()
