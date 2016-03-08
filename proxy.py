#!/usr/bin/python
# -*- coding: utf-8 -*-

import BaseHTTPServer
import shutil
import urllib2
import libinternetotv as tv
import sys
from email.utils import formatdate
import os
import time
import simplejson as json
import datetime

try:
  import xml.etree.cElementTree as ET
except:
  import xml.etree.ElementTree as ET

global PORT
global HOST
global cacheDir
global epg_file
global curr_epg_date
global instant_epg
global itv

instant_epg = True
curr_epg_date = ''
itv = None

def getCache(key):
  
  cfile = cacheDir+key
  
  if os.path.isfile(cfile):
    f = open(cfile, 'r')
    d = f.readlines()
    f.close()
    
    if len(d) < 2:
      return None
    
    if int(d[0]) > int(time.time()):    
      return d[1]
    else:
      os.remove(cfile)
  
  return None

def setCache(key, value, cacheTime):
  
  cfile = cacheDir+key
  
  f = open(cfile, 'w')
  f.write(str(int(time.time())+cacheTime)+'\n')
  f.write(value)
  f.close()
  
  
def fetchEPG():
  
  data = itv.getDayEPG()

  tv = ET.Element("tv")

  for item in data['channels']:
    channel = ET.SubElement(tv, 'channel', id=item['id'])
    name = ET.SubElement(channel, 'display-name').text = item['title']
    icon = ET.SubElement(channel, 'icon', src=item['icon'])
    
  for item in data['epg']:
    if ('channelId' in item) and ('start' in item) and ('end' in item):
      programme = ET.SubElement(tv, 'programme')
      programme.set('channel', item['channelId'])
      programme.set('start', item['start'].strftime('%Y%m%d%H%M%S'))
      programme.set('stop', item['end'].strftime('%Y%m%d%H%M%S'))
      title = ET.SubElement(programme, 'title').text = item['title']
      if 'description' in item:
        description = ET.SubElement(programme, 'desc').text = item['description']
      if 'image' in item:
        icon = ET.SubElement(programme, 'icon', src=item['image'])

  f = open(epg_file % data['dateStr'], 'w')
  tree = ET.ElementTree(tv)
  if sys.version_info >= (2,7):
    tree.write(f, encoding='utf-8', xml_declaration=True)
  else:
    f.write("<?xml version='1.0' encoding='utf-8'?>")
    tree.write(f, encoding='utf-8')
  f.close()
  
def checkEPGFile():
  
  date = datetime.datetime.now()
  dateStr = '-'.join([str(date.year), str(date.month).zfill(2), str(date.day).zfill(2)])
  
  global curr_epg_date
  if curr_epg_date == dateStr:
    return True
  
  if not os.path.isfile(epg_file % dateStr):
    fetchEPG()
    curr_epg_date = dateStr
    return False
  
  return True

class Proxy(BaseHTTPServer.BaseHTTPRequestHandler):
  
  isHead = False
  
  def copyHeaders(self, headers):
    
    self.send_response(200)
    
    for key in headers.keys():
      self.send_header(key, headers.get(key))
      
    self.end_headers()
    
  def fetchChannels(self):
    
    jsondata = getCache('channels')
    data = False
    if jsondata:
      data = json.loads(jsondata)
    
    if not data:
      data = {}
      data['channels'] = itv.getChannels()
      data['updated'] = formatdate(timeval=None, localtime=False, usegmt=True)
      jsondata = json.dumps(data)
      setCache('channels', jsondata, 3600)
      
    return data      
  
  def getChannels(self):    

    data = self.fetchChannels()
    if not data:
      return
    
    content = ''
    content += '#EXTM3U \n'
    
    for channel in data['channels']:
      content += '#EXTINF:-1 tvg-id="%s" tvg-logo="%s",' % (channel['id'], channel['id'])
      content += channel['title'].encode('utf-8')
      content += '\n'
      content += 'http://%s:%s/channel/%s/start.m3u8\n' % (HOST, PORT, channel['id'])
      
    self.send_response(200)
    self.send_header('Accept-Ranges', 'bytes')
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Date', data['updated'])
    self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
    self.send_header('Content-Length', len(content))
    self.end_headers()
    self.wfile.write(content)
  
  def getChannelURL(self, ch_id):
    
    url = getCache('channelURL_'+ch_id)
    if not url:
      ch = itv.getChannelUrls(ch_id)
      url = ch['mp4_hls']
      setCache('channelURL_'+ch_id, url, 300)
      
    return url
  
  def getChannelPath(self, ch_id):
    
    path = getCache('channelPath_'+ch_id)
    if not path or (ch_id == 'delfitv'):
      url = self.getChannelURL(ch_id)
      path = url[0:url.rfind('/')+1]
      setCache('channelPath_'+ch_id, path, 3600)
      
    return path
  
  def getChannel(self, ch_id):    
    
    url = self.getChannelURL(ch_id)      
    
    if not url:
      self.wfile.write(' ')
      return
    
    req = urllib2.urlopen(url)
    self.copyHeaders(req.info())
    shutil.copyfileobj(req, self.wfile)
    
  def getFile(self, ch_id, fileName):
    
    path = self.getChannelPath(ch_id)
    req = urllib2.urlopen(path+fileName)
    self.copyHeaders(req.info())
    shutil.copyfileobj(req, self.wfile)
    
  def getLogo(self, ch_id):
    
    data = self.fetchChannels()
    if not data:
      return
    
    channels = data['channels']
    channel = filter(lambda d: d['id'] == ch_id, channels)
    
    if not channel:
      return
    
    channel = channel[0]
    
    url = channel['icon']
    
    request = urllib2.Request(url)
    
    if self.isHead:
      request.get_method = lambda : 'HEAD'
        
    req = urllib2.urlopen(request)
    
    self.copyHeaders(req.info())
    shutil.copyfileobj(req, self.wfile)
  
  def getEPG(self):    
    
    date = datetime.datetime.now()
    dateStr = '-'.join([str(date.year), str(date.month).zfill(2), str(date.day).zfill(2)])
    
    if instant_epg:
      checkEPGFile()
    
    try:
      f = open(epg_file % dateStr, 'r')
    except:
      time.sleep(1.8)
      self.send_response(404)
      return
      
    date = datetime.datetime.utcnow()
    date = date.replace(minute=0, second=0)
    
    self.send_response(200)
    self.send_header('Accept-Ranges', 'bytes')
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Date', formatdate(timeval=time.mktime(date.timetuple()), localtime=False, usegmt=True))
    self.send_header('Content-Type', 'application/xml')
    self.send_header('Content-Length', os.fstat(f.fileno()).st_size)
    self.end_headers()
    if not self.isHead:
      shutil.copyfileobj(f, self.wfile)
    f.close()
  
  def do_GET(self):
    path = self.path.split('/')
    path = filter(None, path)
    
    if path[0] == 'channels':
      self.getChannels()
    elif path[0] == 'channel':
      if path[2] == 'start.m3u8':
        self.getChannel(path[1])
      else:
        self.getFile(path[1], path[2])
    elif path[0] == 'epg':
      self.getEPG()
    elif path[0] == 'logo':
      self.getLogo(path[1])
    else:
      print "Unsupported request!"
      print path
      self.send_response(440)
        
  def do_HEAD(self):
    self.isHead = True
    self.do_GET()
    pass


def login(user, passw):
  global itv
  if not itv:
    itv = tv.InternetoTV()
  itv.setCredential(user, passw)
  itv.getCookie()
  itv.setDisableCache(True)
  