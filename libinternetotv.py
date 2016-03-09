# -*- coding: utf-8 -*-

import re
import urllib
import urllib2
import sys
import datetime

from StringIO import StringIO
import gzip

from bs4 import BeautifulSoup, SoupStrainer

reload(sys) 
sys.setdefaultencoding('utf8')

import httplib

class InternetoTV(object):
  
  def __init__(self):
    self.USERNAME = ''
    self.PASSWORD = ''
    self.COOKIE = None
    self.HOST = 'www.interneto.tv'
    self.HTTP = None
    self.HTTPS = None
    self.cacheDisabled = False
    self._channels_cache = None
    
  def setDisableCache(self, disabled = True):
    self.cacheDisabled = disabled
    if self.cacheDisabled:
      self.HTTP = None
      self.HTTPS = None

  def getHTTP(self):
    
    if self.cacheDisabled:
      return httplib.HTTPConnection(self.HOST)
    
    if not self.HTTP:      
      self.HTTP = httplib.HTTPConnection(self.HOST)
    
    return self.HTTP
  
  def getHTTPS(self):
    
    if self.cacheDisabled:
      return httplib.HTTPSConnection(self.HOST)
    
    if not self.HTTPS:      
      self.HTTPS = httplib.HTTPSConnection(self.HOST)
      
    return self.HTTPS

  def setCredential(self, username, password):
    self.USERNAME = username
    self.PASSWORD = password
  
  def unzipResponse(self, response):
    
    if response.getheader('Content-Encoding') == 'gzip':
      buf = StringIO(response.read())
      f = gzip.GzipFile(fileobj=buf)
      return f.read()
    else:    
      return response.read()

  def getCookie(self):

    loginData = {}
    loginData['data[AppUser][email]'] = self.USERNAME
    loginData['data[AppUser][password]'] = self.PASSWORD
    loginData['data[AppUser][remember]'] = '1'
    loginData = urllib.urlencode(loginData)

    c = self.getHTTPS()
    c.request("POST", "/prisijungti", loginData, {'Content-type': 'application/x-www-form-urlencoded', 'Accept-encoding': 'gzip'})
    response = c.getresponse()
    fdata = self.unzipResponse(response)

    cookie = response.getheader('set-cookie') 

    ITVAPP = ''
    ITVCOOKIE = ''

    for c in cookie.replace(',',';').split(';'):
      p = c.split('=')
      
      key = p[0].strip()
      if key == 'ITVAPP':
	ITVAPP = p[1].strip()
      if key == 'ITVCOOKIE[remember_me]':
	ITVCOOKIE = p[1].strip()
      
    if ITVAPP and ITVCOOKIE:
      self.COOKIE = 'ITVAPP=%s; ITVCOOKIE[remember_me]=%s' % (ITVAPP, ITVCOOKIE)
      return self.COOKIE
	
    else:
      return None
    
  def setCookie(self, cookie):    
    self.COOKIE = cookie
    
  def n18(self):
    c = self.getHTTP()
    c.request("GET", "/n18/1", headers = {'Cookie': self.COOKIE, 'Accept-encoding': 'gzip'})
    c.getresponse().read()
      
  def getChannelUrls(self, vid):
    
    videoData = {}

    c = self.getHTTP()
    c.request("GET", "/kanalas/" + vid, headers = {'Cookie': self.COOKIE, 'Accept-encoding': 'gzip'})
    response = c.getresponse()
    fdata = self.unzipResponse(response)
    
    if response.getheader('location') and response.getheader('location').startswith('http://www.interneto.tv/n18'):
      self.n18()
      c.request("GET", "/kanalas/" + vid, headers = {'Cookie': self.COOKIE, 'Accept-encoding': 'gzip'})
      fdata = self.unzipResponse(c.getresponse())
      
    soup = BeautifulSoup(fdata, 'html.parser')
    
    ico_logout = soup.find('a', class_='ico-logout')
    if not ico_logout:
      return { 'login_failed' : True }

    player_wrapper = soup.find('div', class_='player-wrapper')
    
    if not player_wrapper:      
      content = soup.find('div', id='content')
      return { 'error' : content.h1.text }

    links = player_wrapper.find_all('a')

    videoData['RTMP'] = links[1]['href'] #RTMP

    epg_first = soup.find('div', id='epg-first')

    img = epg_first.find('img')

    videoData['img'] = img['src'] #IMG

    videoData['title'] = epg_first.find('div', class_='title').string

    videoData['description'] = epg_first.find('div', class_='description').string

    videoData['mp4_hls'] = re.findall(' \[\{type\: \'hls\', file\: \'([^\']*)\'', fdata, re.DOTALL)[0]

    return videoData

  def getChannels(self):
    
    if self._channels_cache:
      return self._channels_cache
    
    result = []
    
    c = self.getHTTP()
    c.request("GET", "/kanalai", headers = {'Accept-encoding': 'gzip'})
    fdata = self.unzipResponse(c.getresponse())
    
    soup = BeautifulSoup(fdata, 'html.parser')
    
    ul = soup.find('ul', class_='channels-list')
    
    for channel in ul.find_all('a'):
      
      ch = {}
      ch['id'] = channel['href'].split('/')[2] 
      ch['icon'] = channel.span.img['src']
      ch['title'] = channel.span.img['alt']
      
      result.append(ch)
    
    self._channels_cache = result    
    return result

  def getVideoCats(self):
    
    cats = []
    
    c = self.getHTTP()
    c.request("GET", "/tvirasai", headers = {'Accept-encoding': 'gzip'})
    fdata = self.unzipResponse(c.getresponse())
    
    soup = BeautifulSoup(fdata, 'html.parser')    
    
    wrappers = soup.find_all('div', class_='carousel-wrapper')
    for wrapper in wrappers: 
      
      cat = {}
      
      cat['id'] = wrapper.find('div', class_='iosslider')['id']      
      cat['title'] = wrapper.previous_sibling.previous_sibling.span.text
      
      cats.append(cat)
    
    return cats
  
  def getVideoCat(self, cid):
    
    videos = []
    
    c = self.getHTTP()
    c.request("GET", "/tvirasai", headers = {'Accept-encoding': 'gzip'})
    fdata = self.unzipResponse(c.getresponse())
    
    soup = BeautifulSoup(fdata, 'html.parser')
    
    cat = soup.find('div', id=cid)
    
    vids = cat.find_all('div', class_='slide')
    for vid in vids:
      
      video = {}
      
      video['image'] = vid.img['src']
      video['url'] = vid.a['href']
      video['title'] = vid.find('span', class_='title').text
      video['date'] = vid.find('span', class_='time-day').text
      
      videos.append(video)
      
    return videos
  
  def getVideoURL(self, url):
    
    videoData = {}
    
    c = self.getHTTP()
    c.request("GET", url, headers = {'Cookie': self.COOKIE, 'Accept-encoding': 'gzip'})
    response = c.getresponse()
    fdata = self.unzipResponse(response)
    
    if response.getheader('location') and response.getheader('location').startswith('http://www.interneto.tv/n18'):
      self.n18()
      c.request("GET", url, headers = {'Cookie': self.COOKIE, 'Accept-encoding': 'gzip'})
      fdata = self.unzipResponse(c.getresponse())
    
    soup = BeautifulSoup(fdata, 'html.parser')
    
    ico_logout = soup.find('a', class_='ico-logout')
    if not ico_logout:
      return { 'login_failed' : True }
    
    player_wrapper = soup.find('div', class_='player-wrapper')

    links = player_wrapper.find_all('a')

    videoData['mp4_hls'] = links[1]['href']
    
    if not videoData['mp4_hls'].startswith('http'):
      videoData['mp4_hls'] = re.findall('\[\{sources\: \[\{file\: "([^"]*)"', fdata, re.DOTALL)[0]

    epg_first = soup.find('div', id='epg-first')

    img = epg_first.find('img')

    videoData['img'] = img['src'] #IMG

    videoData['title'] = epg_first.find('div', class_='title').string
    
    return videoData
  
  def getDayEPG(self, dayAplha=0):
    
    date = datetime.datetime.now()
    
    if dayAplha != 0:
      date = date + datetime.timedelta(days=dayAplha)
    
    dateStr = '-'.join([str(date.year), str(date.month).zfill(2), str(date.day).zfill(2)])
    date = date.replace(second=0)
    
    url = '/tvprograma/'+dateStr
    
    c = self.getHTTP()
    c.request("GET", url, headers = {'Accept-encoding': 'gzip'})
    response = c.getresponse()
    fdata = self.unzipResponse(response)
    
    #soup = BeautifulSoup(fdata, 'html.parser')
    
    channels = self.getChannels()
    
    channelsU = []
    
    #channels_slider_container = soup.find('div', id='channels-slider-container')    
    channels_slider_container = BeautifulSoup(fdata, 'html.parser', parse_only=SoupStrainer('div', id='channels-slider-container'))
    
    for item in channels_slider_container.find_all('div', class_='slide'):
      img = item.find('img')
      channel = {}
      title = img['alt']
      channel['title'] = title
      channel['icon'] = img['data-original']
      channel['id'] = filter(lambda d: d['title'] == title, channels)[0]['id']
      channelsU.append(channel)    
    
    i = 0
    channelsEPG = []
    
    #tv_guide_slider = soup.find('div', id='tv-guide-slider')
    tv_guide_slider = BeautifulSoup(fdata, 'html.parser', parse_only=SoupStrainer('div', id='tv-guide-slider'))
    
    for item in tv_guide_slider.find_all('div', class_='slide'):
      tv_guide_items = item.find_all('div', class_='tv-guide-item')

      chId = channelsU[i]['id']
      tvmin = 0
      tvday = 0
      
      if tv_guide_items:        
        
        previuos_programme = None
        
        for item in tv_guide_items:
          
          programme = {}
          
          programme['channelId'] = chId
          
          p = item.find('p', class_='title')
          a = p.find('a')
          if a:
            programme['record'] = a['href']
            programme['title'] = a.get_text().strip()
          else:
            programme['title'] = p.get_text().strip()
            
          img = item.find('img')
          if img and ('data-original' in img.attrs):
            programme['image'] = img['data-original']
            
          desc = item.find('p', class_='description')
          if desc:
            programme['description'] = p.string.strip()
            
          time_start = item.find('p', class_='time-start').string.strip()
          if time_start and (len(time_start) == 5):
            h = int(time_start[0:2])
            m = int(time_start[3:5])            
            d = date.replace(hour=h, minute=m)
            
            tvminnew = h*60 + m
            if tvminnew < tvmin:
              tvday += 1              
            tvmin = tvminnew
              
            d = d + datetime.timedelta(days=tvday)            
            programme['start'] = d
            
            if previuos_programme:
              previuos_programme['end'] = programme['start']
              
          length = item.find('span', class_='time-duration')
          if length:
            length = length.string
            
            if length:
              programme['length'] = self.lengthStrToMin(length.strip())
          
          previuos_programme = programme            
          
          channelsEPG.append(programme)
          
      i+= 1
      
    for channel in channelsEPG:
      if 'end' not in channel:
        if 'length' in channel:
          channel['end'] = channel['start'] + datetime.timedelta(minutes=channel['length'])
    
    result = {}
    result['channels'] = channelsU
    result['epg'] = channelsEPG
    result['dateStr'] = dateStr
    
    return result
  
  def lengthStrToMin(self, length):
    
    result = 0
    
    for i in length.split('.'):
      parts = i.strip().split(' ')
      if len(parts) == 2:
        if parts[1] == 'min':
          result += int(parts[0])
        elif parts[1] == 'val':
          result += int(parts[0]) * 60
          
    return result
    