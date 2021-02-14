import numpy as np
from tomita.legacy import pysynth_c as Synth
import random
import wave
import os

BPM = 90

def mix_wavs(input_fns, out_fn="temp/mix.wav"):
    """Given a list of input wav file names, mixes them together and creates a new wav file as out_fn"""
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



def append_wavs(input_fns, out_fn="temp/mix.wav"):
    """
       Given last of input wav filenames input_fns, joins them together into output file out_fn.
       Adapted from https://stackoverflow.com/questions/2890703/how-to-join-two-wav-files-using-python.
    """

    data= []
    for infile in input_fns:
        w = wave.open(infile, 'rb')
        data.append( [w.getparams(), w.readframes(w.getnframes())] )
        w.close()
        
    output = wave.open(out_fn, 'wb')
    output.setparams(data[0][0])
    for i in range(len(data)):
        output.writeframes(data[i][1])

    output.close()


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
    def from_chord(cls, chord, length):
        """Return a chord tone note with length from the provided chord"""
        valid_notes = set(chord.scale.notes)
        n = random.sample(valid_notes, 1)[0]

        return Note(n, length)
    

    def make_sound(self, fn):
        """Writes wav of note to filename fn"""
        Synth.make_wav([(self.name, self.length)], fn=f'{fn}', bpm=BPM)


class Chord:
    valid_chords = {"major", "minor", 'm7b5'}
    
    def __init__(self, root, kind):
        """Given root note as a string or note object and chord type 'kind' from set above, construct Chord object"""
        if str(root) not in Note.valid_notes:
            raise ValueError("Invalid root note")
        if kind not in Chord.valid_chords:
            raise ValueError(f"Invalid Chord: please select from {Chord.valid_chords}")
        
        self.root = str(root)
        self.kind = kind
        self.scale = Scale.from_chord(self)
        self.notes = [self.scale.notes[i] for i in (0, 2, 4)]
        self.song = [[(c, i)] for c, i in zip(self.notes, [1,1,1])]
        self.chordmap = []
    

    def make_sound(self):
        """Writes self.notes into individual wav files then combines the wav files into an output wavfile"""
        chords = os.listdir('chords')
        if f"{self.root}{self.kind}.wav" not in chords:
            for i, _ in enumerate(self.notes):
                Synth.make_wav(self.song[i], fn=f"notes/{i}.wav", bpm=BPM)
            
            mix_wavs([f"notes/{i}.wav" for i, _ in enumerate(self.notes)], out_fn=f"chords/{self.root}{self.kind}.wav")
    

    def to_child(self):
        cmap = {'major': MajorChord,
                'minor': MinorChord,
                'm7b5': M7B5Chord}
        return cmap[self.kind](self.root)

    def next_chords(self):
        """Based on the current chord, returns a list of Chord children which make 'harmonic sense' to choose next"""
        return [Chord(self.scale.notes[i], random.choice(self.chordmap[i])).to_child() for i in (0, 1, 3, 4, 6)]
    

class MajorChord(Chord):
    def __init__(self, root):
        super().__init__(root, 'major')
        self.chordmap = {0: ['major', 'minor'],
                    1: ['minor'],
                    3: ['major'],
                    4: ['major'],
                    6: ['m7b5']}


class MinorChord(Chord):
    def __init__(self, root):
        super().__init__(root, 'minor')
        self.chordmap = {0: ['major', 'minor'],
                    1: ['m7b5', 'minor'],
                    3: ['major'],
                    4: ['minor'],
                    6: ['major']}


class M7B5Chord(Chord):
    def __init__(self, root):
        super().__init__(root, 'm7b5')
        self.chordmap = {0: ['m7b5'],
                    1: ['major'],
                    3: ['minor'],
                    4: ['major', 'minor'],
                    6: ['major']}
    
    

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
    def construct_mode(cls, root, pattern):
        """Given a list of intervals pattern, returns list of notes corresponding to the mode"""

        #This feels ugly but it works for now, can make more efficient later
        cs = cls.chromatic_scale*2
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
            

    def from_ionian_shift(self, root, shift):
        """given root note and integer amount to shift rightwards, returns the correct mode pattern as a list of strings"""

        p = self.construct_mode(root, self.patterns['Ionian'])
        shift = shift
        return p[shift:] + p[:shift]
    

    def build_relative_mode(self, root, mode):
        """Given Ionian root note as str: 'a#'/etc. and mode as str: 'Ionian'/'Dorian'/etc. 
        returns list of strings corresponding to relative mode"""
        p = self.from_ionian_shift(root, self.mode_shifts[mode])
        return p
    

    @classmethod
    def build_mode(cls, root, mode):
        shift = cls.mode_shifts[mode]
        pattern = cls.patterns['Ionian'][shift:] + cls.patterns['Ionian'][:shift]
        return cls.construct_mode(root, pattern)


    @classmethod
    def from_chord(cls, chord):
        """Returns random scale based on provided chord object."""
        if chord.kind not in Scale.valid_scales:
            raise ValueError("Scale unknown for provided chord")

        if chord.kind == 'major':
            sc= cls.build_mode(chord.root, random.choice(['Ionian', 'Mixolydian', 'Lydian']))
        elif chord.kind == 'minor':
            sc= cls.build_mode(chord.root, random.choice(['Dorian', 'Aeolian']))
        else:
            sc = cls.build_mode(chord.root, random.choice(['Locrian', 'Phrygian']))
        
        return Scale(sc)
    

    def generate_riff(self):
        """
        Returns a randomly-generated riff based on the current chord's chord/scale tones:
        a list of Note objects corresponding to the notes that should be played at each 1/16 time step in the riff
        """
        # Create note list 'mask' and set random energy level for riff and # of chord tones in riff
        mask = ['r']*16
        n_chord_tones = random.randint(2, 5)
        energy = random.choice([0.4, 0.6, 0.8])

        # Functions for generating random chord/scale tones
        chord_tone = lambda: random.choice([self.notes[i] for i in (0, 2, 4)])
        scale_tone = lambda: random.choice(self.notes)

        # Generate list of note starting positions, chord tones to use, and lengths of those chord tones (1/16 or 1/8 note)
        start_notes = random.sample([i*2 for i in range(8)], n_chord_tones)
        chord_tones = [chord_tone() for n in start_notes]
        lengths = [random.choice([0, 1]) for c in chord_tones]

        # Iterate over start positions placing chord tones
        # Chord tones are the notes found in a chord, and in jazz/music solos
        # Create a sense of resolution/ground the riff in the harmonic context
        for pos, c, l in zip(start_notes, chord_tones, lengths):
            # Place chord tone
            mask[pos] = c

            # If 1/8 note, place second 1/16 note
            if l:
                mask[pos+1] = c
        
        # Generate scale tones, notes which imply an extension of the chord to some new sound
        # Including possibility for chord tones to be here to increase variety/make riffs sound more grounded
        # Frequency depends on energy determined at start of riff generation
        for i, v in enumerate(mask):
            if v == 'r' and random.random() < energy:
                mask[i] = scale_tone()

        return [Note(v, 16) for v in mask]


class Bar:
    # Variable for keeping track of last chord/note for harmonic/melodic continuity
    last = None

    def __init__(self):
        self.chords = []
        self.notes = []

    
    def build_chords(self):
        """Populates self.chords with randomly-generated chord progression. 
        Assumes Bar.last holds last chord of most recent generated chord"""
        
        for i in range(4):
            if self.last == None:
                self.last = MajorChord('c')
            
            new_chord = random.choice(self.last.next_chords())
            self.chords.append(new_chord)
            self.last = new_chord


    def build_notes(self):
        """Populates self.notes with randomly-generated melody based on chords in self.chords. 
        In a future version, maybe Place chord tones -> Connect with riffs...
        ...today, randomly choose length and notes and go for it!"""
        for c in self.chords:
            
            # Generate riff sounds terrible
            for note in c.scale.generate_riff():
                self.notes.append(note)

            #t = random.choice([4, 8, 16, 8, 8, 8, 16])
            #for i in range(t):
            #    self.notes.append(Note.from_chord(c, t))



    def to_wav(self, out_fn):
        """Writes chords and notes to output filename"""

        # Synthesize chords, create harmony file
        chords = []
        for c in self.chords:
            c.make_sound()
            chords.append(f"chords/{c.root}{c.kind}.wav")

        append_wavs(chords, 'harmony.wav')

        # Synthesize notes, create melody file
        i = 0
        notes = []
        for n in self.notes:
            fn = f"notes/note_{i}.wav"
            n.make_sound(fn)
            notes.append(fn)
            i += 1

        # Mix harmony/melody
        append_wavs(notes, 'melody.wav')
            
        mix_wavs(['harmony.wav', 'melody.wav'], out_fn=out_fn)


def main(n, fn):
    for i in range(n):
        b = Bar()
        b.build_chords()
        b.build_notes()
        b.to_wav(fn)

    
if __name__ == "__main__":
    main(4, 'output')
