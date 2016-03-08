import urllib2
import datetime
from HTMLParser import HTMLParser


class MyHTMLParser(HTMLParser):
  
  def __init__(self, date):    
    HTMLParser.__init__(self)
    self.channels_slider_container = 0
    self.tv_guide_slider = 0
    self.slide = 0
    self.tv_guide_item = 0
    self.epg_title = 0
    self.epg_description = 0
    self.epg_time_start = 0
    self.date = date.replace(second=0)
    
    self.levels = []
    
    self.channels_list = []
    self.epg_list = []
    self.currentChannel = None
    self.epgItem = None    
  
  def handle_starttag(self, tag, attrs):
    
    self.levels.append(tag)
    attrs = dict(attrs)    
    
    if tag == 'div':
      if 'id' in attrs:
        aid = attrs['id']
        
        if aid == 'channels-slider-container':
          self.channels_slider_container = len(self.levels)
        elif aid == 'tv-guide-slider':
          self.tv_guide_slider = len(self.levels)
      
      if 'class' in attrs:
        class_ = attrs['class'].strip().split(' ')
        
        if 'slide' in class_:
          self.slide = len(self.levels)
          
          if self.channels_slider_container > 0:
            self.currentChannel = {}
            self.channels_list.append(self.currentChannel)
            
        elif 'tv-guide-item' in class_:
          self.epgItem = {}
          self.epg_list.append(self.epgItem)
          self.tv_guide_item = len(self.levels)
          
    elif tag == 'img':
      
      if self.slide > 0:        
        if self.channels_slider_container > 0:
          if type(self.currentChannel) == dict:
            title = attrs['alt']
            self.currentChannel['title'] = title
            self.currentChannel['icon'] = attrs['data-original']
            
        elif self.tv_guide_item > 0:
          if 'data-original' in attrs:
            if type(self.epgItem) == dict:
              self.epgItem['icon'] = attrs['data-original']          
    
    elif tag == 'p':
      if self.tv_guide_item > 0:
        if 'class' in attrs:
          class_ = attrs['class'].strip().split(' ')  
          
          if 'title' in class_:
            self.epg_title = len(self.levels)
            
          elif 'description' in class_:
            self.epg_description = len(self.levels)
          elif 'time-start' in class_:
            self.epg_time_start = len(self.levels)            
          
    elif tag == 'a':
      if self.epg_title > 0:
        if type(self.epgItem) == dict:
          self.epgItem['record'] = attrs['href']
          
    
  def handle_endtag(self, tag):
    
    if tag in self.levels:
      
      t = ''
      while t != tag:
        t = self.levels.pop()
        
    if self.channels_slider_container > len(self.levels):
      self.channels_slider_container = 0
      
    if self.tv_guide_slider > len(self.levels):
      self.tv_guide_slider = 0
      
    if self.slide > len(self.levels):
      self.slide = 0
      
    if self.tv_guide_item > len(self.levels):
      self.tv_guide_item = 0
      
    if self.epg_title > len(self.levels):
      self.epg_title = 0
      
    if self.epg_description > len(self.levels):
      self.epg_description = 0
      
    if self.epg_time_start > len(self.levels):
      self.epg_time_start = 0
      
  def handle_data(self, data):
    data = data.strip()
    if data:
      
      if type(self.epgItem) == dict:
        if self.epg_title > 0:       
          self.epgItem['title'] = data
        elif self.epg_description > 0:
          self.epgItem['description'] = data
        elif self.epg_time_start > 0:
          self.parseDate(data)
  
  def parseDate(self, dateStr):
    if dateStr and (len(dateStr) == 5):
      h = int(dateStr[0:2])
      m = int(dateStr[3:5])            
      d = date.replace(hour=h, minute=m)
      
      tvminnew = h*60 + m
      if tvminnew < tvmin:
        tvday += 1              
      tvmin = tvminnew
        
      d = d + datetime.timedelta(days=tvday)            
      programme['start'] = d

date = datetime.datetime.now()
dateStr = '-'.join([str(date.year), str(date.month).zfill(2), str(date.day).zfill(2)])

req = urllib2.urlopen('http://www.interneto.tv/tvprograma/'+dateStr)
parser = MyHTMLParser(date)
parser.feed(req.read())
#print parser.channels_list
print parser.epg_list
