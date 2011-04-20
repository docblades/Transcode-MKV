#!/usr/bin/python
# Created By: Christian Blades <christian DOT blades AT docblades DOT com>
# Requires mkvtoolnix, python-argparse, ffmpeg, libfaac and gpac

import os, uuid, argparse, mkvinfo_parser, re, subprocess

MKVEXTRACT = 'mkvextract'
MKVINFO = 'mkvinfo-text'
FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'
AAC = 'libfaac'
MP4BOX = 'MP4Box'

def sanitize_in(inStr):
    clean = re.sub("[\n;&]", " ", inStr).strip()
    return clean

def get_audio_rate(path):
    """ Uses ffprobe and grabs the kb/s from the bitrate line"""
    #pout, perr = os.popen4("{0} {1}".format(FFPROBE, path))
    p = subprocess.Popen("{0} {1}".format(FFPROBE, path),
                         shell=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         close_fds=True)
    perr = p.stdout
    bitrate = None
    reBitrate = re.compile("bitrate: ([0-9]+) kb/s")
    for line in perr:
        match = reBitrate.findall(line)
        if len(match) > 0:
            bitrate = match[0]
            break
    if bitrate is None:
        raise Exception("ffprobe did not return a bitrate for {0}".format(path))
    perr.close()
    return bitrate

def get_video_fps(path):
    """ Parse MKVInfo into a tree, then extract the video FPS """
    cmdStr = "{0} {1}".format(MKVINFO, path)
    myFile = os.popen(cmdStr)
    myTree = mkvinfo_parser.parse(myFile)
    myFile.close()
    fps = mkvinfo_parser.get_vid_fps(myTree)
    return fps

def existing_file(path):
    """ Argparser type """
    path = sanitize_in(path)
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError("{0} does not exist".format(path))
    return path

def new_file(path):
    """ Argparser type """
    path = sanitize_in(path)
    try:
        aFile = open(path, 'w')
        aFile.close()
    except IOError:
        raise argparse.ArgumentTypeError("{0} is a bad path, or you do not have write permissions")
    return path

def existing_dir(path):
    """ Argparser type """
    path = sanitize_in(path)
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError("{0} is not a valid path".format(path))
    return path
    
parser = argparse.ArgumentParser(
    description="Transcodes the audio from a MKV into AAC and then repacks into an avi")
parser.add_argument('inFile', help='Input Filename',
                    type=existing_file, metavar='FILE')
parser.add_argument('--out', help='Output Filename',
                    type=new_file)
parser.add_argument('--brate', help='Audio Bitrate (0 = same as source)',
                    type=int, default=0, nargs=1)
parser.add_argument('--cleanup', help='Clean up temporary files',
                    default=False, type=bool, nargs=1, metavar='True|False')
parser.add_argument('--tempdir', help='Where to put the temp files. Default is current directory."',
                    default=os.path.curdir, type=existing_dir)
parser.add_argument('--reverse', help='Audio and Video tracks are in opposite order',
                    default=False, type=bool, nargs=1, metavar='True|False')

theVars = parser.parse_args()
theuuid = str(uuid.uuid1())
tmpPath = os.path.join(theVars.tempdir, theuuid)

if theVars.out is None:
    theVars.out = "{0}.mp4".format(os.path.splitext(theVars.inFile)[0])

print "===Extracting audio and video tracks"
if theVars.reverse:
    cmdStr = "{0} tracks {1} 1:{2}.dts 2:{2}.264"
else:
    cmdStr = "{0} tracks {1} 1:{2}.264 2:{2}.dts"
cmdStr = cmdStr.format(MKVEXTRACT, theVars.inFile, tmpPath)
os.system(cmdStr)

print "===Converting audio"
brate = theVars.brate
if brate == 0:
    brate = get_audio_rate("{0}.dts".format(tmpPath))
cmdStr = "{0} -i {1}.dts -acodec libfaac -ab {2}k {1}.aac"
cmdStr = cmdStr.format(FFMPEG, tmpPath, brate)
os.system(cmdStr)

try:
    os.remove("{0}.dts".format(tmpPath))
except OSError:
    print "Failed to remove temp file {0}.dts".format(tmpPath)

print "===Repacking as MP4"
fps = get_video_fps(theVars.inFile)
cmdStr = "{0} -new {1} -add {2}.264 -add {2}.aac -fps {3}"
cmdStr = cmdStr.format(MP4BOX, theVars.out, tmpPath, fps)
os.system(cmdStr)

try:
    os.remove("{0}.264".format(tmpPath))
    os.remove("{0}.aac".format(tmpPath))
except OSError:
    print "There was an error while cleaning up temporary files. Sorry."
