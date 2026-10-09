"""Monotonic sample scheduler; never integrates the number of timer ticks."""
from bisect import bisect_right,bisect_left
from fractions import Fraction
from time import monotonic

class PlaybackClock:
    def __init__(self,times,duration,*,clock=monotonic):
        self.times=tuple(float(t) for t in times)
        if any(a>=b for a,b in zip(self.times,self.times[1:])):
            raise ValueError('Nonmonotonic sample timestamps')
        self.duration=float(duration)
        if self.times and (self.times[0]<0 or self.times[-1]>=self.duration):
            raise ValueError('Sample outside duration')
        self._clock=clock
        self.playing=False
        self.position=0.
        self._started=0.
        self._base=0.

    def target(self):
        return min(self.duration,self._base+max(0,self._clock()-self._started)) if self.playing else self.position

    def index(self):
        return max(0,bisect_right(self.times,self.target())-1) if self.times else -1

    def tick(self):
        current=self.target()
        if self.playing and current>=self.duration:
            self.position=self.duration;self.playing=False
        else:self.position=current
        return self.index()

    def play(self):
        if not self.times:return
        if self.target()>=self.duration:self.position=0.
        self._base=self.position;self._started=self._clock();self.playing=True

    def pause(self):
        if self.playing:self.position=self.target()
        self.playing=False

    def seek_index(self,index):
        self.pause()
        if not self.times:return -1
        index=max(0,min(len(self.times)-1,index))
        self.position=self.times[index];return index

    def seek_seconds(self,value):
        self.pause()
        if not self.times:return -1
        i=bisect_left(self.times,float(value))
        if i==0:return self.seek_index(0)
        if i>=len(self.times):return self.seek_index(len(self.times)-1)
        return self.seek_index(i-1 if float(value)-self.times[i-1]<=self.times[i]-float(value) else i)
