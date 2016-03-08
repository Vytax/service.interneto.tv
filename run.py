#!/usr/bin/python
# -*- coding: utf-8 -*-

import SocketServer
import proxy
import sys
import config

proxy.HOST = config.HOST
proxy.PORT = config.PORT
proxy.cacheDir = config.CACHE_DIR
proxy.epg_file = config.EPG_FILE

if __name__ == '__main__':
    
  proxy.login(config.EMAIL, config.PASSWORD)

  #httpd = SocketServer.ForkingTCPServer(('', config.PORT), proxy.Proxy)
  httpd = SocketServer.ThreadingTCPServer(('', config.PORT), proxy.Proxy)
  print "serving at port", config.PORT

  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    sys.exit()