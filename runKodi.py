#!/usr/bin/python
# -*- coding: utf-8 -*-

import SocketServer
import proxy
import xbmc
import xbmcaddon
import xbmcvfs
import thread

tmpPath = xbmc.translatePath('special://temp')+'/itv/'
if not xbmcvfs.exists(tmpPath):
  xbmcvfs.mkdir(tmpPath)

PORT = 9080
proxy.HOST = '127.0.0.1'
proxy.PORT = PORT
proxy.cacheDir = tmpPath
proxy.epg_file = proxy.cacheDir + 'epg_%s.xml'
proxy.instant_epg = False

class ITVMonitor(xbmc.Monitor):

  def __init__(self):
    xbmc.Monitor.__init__(self)
    
  def onSettingsChanged(self):
    
    email = settings.getSetting('email')
    password = settings.getSetting('password')
    
    if email and password:
      proxy.login(email, password)
    
monitor = ITVMonitor()    

def epg_thread_func():
  
  while not monitor.abortRequested():
    if proxy.checkEPGFile():    
      xbmc.sleep(1000)  

if __name__ == '__main__':  
  
  xbmc.executebuiltin('StopPVRManager')
  
  settings = xbmcaddon.Addon(id='service.interneto.tv')
  email = settings.getSetting('email')
  password = settings.getSetting('password')

  if not email or not password:
    xbmc.executebuiltin('Addon.OpenSettings(service.interneto.tv)')
    email = settings.getSetting('email')
    password = settings.getSetting('password')

  proxy.login(email, password)
  
  thread.start_new_thread( epg_thread_func, () )
  
  #httpd = SocketServer.ForkingTCPServer(('', PORT), proxy.Proxy)
  httpd = SocketServer.ThreadingTCPServer(('', PORT), proxy.Proxy)
  print "serving at port", PORT
  
  
  xbmc.executebuiltin('StartPVRManager')
  
  httpd.socket.settimeout(1)
  while not monitor.abortRequested():
    httpd.handle_request()
    xbmc.sleep(100)

  