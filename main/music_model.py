import numpy as np
from tomita.legacy import pysynth_b as Synth
import random
import wave


def mix_wavs(input_fns, out_fn="./mix.wav"):
    """Given a list of input filenames, writes a mix of all inputs into an output wav at out_fn"""
    # Shoutout to https://stackoverflow.com/questions/4039158/mixing-two-audio-files-together-with-python
    # for the handy solution to mixing wavs in python

    wavs = [wave.open(fn) for fn in input_fns]
    frames = [w.readframes(w.getnframes()) for w in wavs]

    # here's efficient numpy conversion of the raw byte buffers
    # '<i2' is a little-endian two-byte integer.
    samples = [np.frombuffer(f, dtype='<i2') for f in frames]
    samples = [samp.astype(np.float64) for samp in samples]

    # mix as much as possible
    n = min(map(len, samples))
    mix = samples[0][:n] + samples[1][:n]

    # Save the result
    mix_wav = wave.open(out_fn, 'w')
    mix_wav.setparams(wavs[0].getparams())

    # before saving, we want to convert back to '<i2' bytes:
    mix_wav.writeframes(mix.astype('<i2').tobytes())
    mix_wav.close()


class Note:
    valid_notes = set(['a', 'a#', 'b', 'c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#']).union({'r'})
    valid_lengths = {2**i for i in range(5)}

    def __init__(self, name, length):
        """Given root note as a string or note object and chord type 'kind' from set above, construct Chord object"""

        if name not in Note.valid_notes:
            raise ValueError("Invalid Note Name")
        elif length not in Note.valid_lengths:
            raise ValueError("Invalid Note Length")

        self.name = name
        self.length = length
    

    def __repr__(self):
        return self.name, self.length
    
    def __str__(self):
        return self.name

    @classmethod
    def from_chord(cls, chord):
        """Constructs a note as a random sample from a chord"""
        valid_notes = Note.valid_notes.intersection(chord.scale)

        l = random.sample(Note.valid_lengths, 1)
        n = random.sample(valid_notes, 1)
        return Note(n, l)


class Chord:
    valid_chords = {"major", "minor", 'm7b5'}
    
    def __init__(self, root, kind):
        """Given root note as a string or note object and chord type 'kind' from set above, construct Chord object"""
        if str(root) not in Note.valid_notes:
            raise ValueError("Invalid root note")
        if kind not in Chord.valid_chords:
            raise ValueError(f"Innvalid Chord: please select from {Chord.valid_chords}")
        
        self.root = str(root)
        self.kind = kind
        self.scale = Scale.from_chord(self)
        self.notes = [self.scale.notes[i] for i in (0, 2, 4)]
        self.song = [[(c, i)] for c, i in zip(self.notes, [1,1,1])]
    

    def make_sound(self):
        """Writes self.notes into individual wav files in cd then combines the wav files into an output wavfile"""
        for i, _ in enumerate(self.notes):
            Synth.make_wav(self.song[i], fn=f"{i}.wav")
        
        mix_wavs([f"{i}.wav" for i, _ in enumerate(self.notes)], out_fn=f"{self.root}{self.kind}.wav")
        

        


class Scale:
    chromatic_scale = ['a', 'a#', 'b', 'c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#']
    valid_scales = {'major', 'minor', 'm7b5'}
    patterns = {'Ionian': [2, 2, 1, 2, 2, 2, 1]}
    mode_shifts = {'Ionian': 0,
                   'Dorian': 1,
                   'Phrygian': 2,
                   'Lydian': 3,
                   "Mixolydian": 4,
                   "Aeolian": 5,
                   "Locrian": 6}
    
    def __init__(self, notes):
        """Given root note root and scale type kind, construct scale"""
        self.notes = notes
    
    def __str__(self):
        return str(self.notes)
        
    @classmethod
    def construct_mode(self, root, pattern):
        """Given a list of intervals pattern, returns list of notes corresponding to the mode"""

        #This feels ugly but it works for now, can make more efficient later
        cs = self.chromatic_scale*2
        notes = []

        # iterating over repeated chromatic scale
        i = 0
        p = None
        for note in cs:
            # when you find root, append index
            if str(note) == str(root):
                notes.append(i)
                # fill out pattern-> break loop
                for p in pattern:
                    i+=p
                    notes.append(i)
                break
                
            
            i += 1

            
        return [cs[i] for i in notes]
            

    @classmethod
    def from_ionian_shift(self, root, shift):
        """given root note and integer amount to shift rightwards, returns the correct mode pattern as a list of strings"""

        p = self.construct_mode(root, self.patterns['Ionian'])
        shift = shift
        return p[shift:] + p[:shift]
    
    @classmethod
    def build_relative_mode(self, root, mode):
        """Given root note as str: 'a#'/etc. and mode as str: 'Ionian'/'Dorian'/etc. returns list of strings corresponding to relative mode"""
        p = self.from_ionian_shift(root, self.mode_shifts[mode])
        return p
    
    @classmethod
    def build_mode(self, root, mode):
        shift = self.mode_shifts[mode]
        pattern = self.patterns['Ionian'][shift:] + self.patterns['Ionian'][:shift]
        return self.construct_mode(root, pattern)


    @classmethod
    def from_chord(cls, chord):
        if chord.kind not in Scale.valid_scales:
            raise ValueError("Scale unknown for provided chord")

        if chord.kind == 'major':
            sc= cls.build_mode(chord.root, random.choice(['Ionian', 'Mixolydian', 'Lydian']))
        elif chord.kind == 'minor':
            sc= cls.build_mode(chord.root, random.choice(['Dorian', 'Phrygian', 'Aeolian']))
        else:
            sc = cls.build_mode(chord.root, random.choice(['Locrian', 'Phrygian']))
        
        return Scale(sc)


class Bar:
    # Variable for keeping track of last chord for harmonic continuity
    last = None

    def __init__(self):
        self.chords = []
        self.notes = []


    
    def build_chords(self):
        """Populates self.chords with randomly-generated chord progression. 
        Assumes Bar.last holds last chord of most recent generated chord"""
        pass

    def build_notes(self):
        """Populates self.notes with randomly-generated melody based on chords in self.chords. 
        Place chord tones -> Connect with riffs"""
        pass


    def to_wav(self, fn):
        """Writes chords and notes to output filename"""
        pass

        
def main():
    n = Note('c#', 1)
    c = Chord(n, 'major')
    s = c.scale
    c.make_sound()

    
if __name__ == "__main__":
    main()
