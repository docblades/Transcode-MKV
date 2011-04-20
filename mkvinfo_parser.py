#!/usr/bin/python
# Created by Christian Blades <christian dot blades at docblades dot com>

from xml.etree.cElementTree import Element, ElementTree
from urllib import quote_plus as quote
import re

def _getData(line):
    name, text = None, None
    
    div = line.find(':')
    if div == -1:
        name = quote(line.strip())
    else:
        name = quote(line[:div].strip())
        text = line[div + 1:].strip()

    return name, text

def parse(theFile):
    elStack = []
    root = []
        
    for line in theFile:

        start = line.find("+ ")
        if (start == -1):
            continue
        else:
            name, text = _getData(line[start + 2:])
            
            myEl = Element(name)
            myEl.text = text
            
            if start == 0:                
                elStack = [[0, myEl]]
                root.append(myEl)
            else:                
                if start > elStack[-1][0]:
                    elStack[-1][1].append(myEl)
                    elStack.append([start, myEl])
                else:
                    while(elStack[-1][0] > start):
                        elStack.pop()
                        
                    elStack.pop()
                    elStack[-1][1].append(myEl)
                    elStack.append([start, myEl])

    rootNode = Element("root")

    for el in root:
        rootNode.append(el)
        
    return ElementTree(rootNode)

class TrackNotFoundException(Exception): pass
class InvalidTrackException(Exception): pass

def get_tracks(elTree):
    """Returns a list of tracks"""
    tracks = elTree.findall("//A+track")
    if tracks is None:
        raise TrackNotFoundException("No tracks found")
    return tracks

def get_track_by_type(elTree, trackType):
    """Returns the first found track of the specified type"""
    tracks = get_tracks(elTree)
    theTrack = None
    for track in tracks:
        if track.find("Track+type").text == trackType:
            theTrack = track
            break
        
    if theTrack is None:
        raise TrackNotFoundException("No {0} track found".format(trackType))

    return theTrack

def get_fps(trackEl):
    """Given a track element, extracts and returns the FPS"""
    dur = trackEl.find("Default+duration")
    if dur is None:
        raise InvalidTrackException("No 'Default duration' element found in this track")
    results = re.findall("\(([0-9\.]{6}) fps", dur.text)
    if len(results) == 0:
        raise InvalidTrackException("No FPS data found in this track")
    return results[0]

def get_audio_fps(elTree):
    audioTrack = get_track_by_type(elTree, "audio")
    return get_fps(audioTrack)

def get_vid_fps(elTree):
    videoTrack = get_track_by_type(elTree, "video")
    return get_fps(videoTrack)
