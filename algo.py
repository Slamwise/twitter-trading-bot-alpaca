import sys
#import logging

def algo(self):
  ####################EMAILS######################
  import smtplib
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

  # The mail addresses and password
  sender_address = ''
  sender_pass = ''
  receiver_address = ''

  # Setup MIME
  message = MIMEMultipart()
  message['From'] = 'Trading Bot'
  message['To'] = receiver_address
  message['Subject'] = 'TT3 Algo'  # The subject line

  ####################TWEETS######################
  import tweepy
  import os
  import pandas as pd
  import time

  #Authenticate Twitter API
  consumer_key = ""
  consumer_secret = ""
  access_token = ""
  access_token_secret = ""

  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(access_token, access_token_secret)
  api = tweepy.API(auth,wait_on_rate_limit=True)

  #Get tweets
  username = ''
  count = 1
  try:     
    # Creation of query method using parameters
    tweets = tweepy.Cursor(api.user_timeline,id=username).items(count)
    
    # Pulling information from tweets iterable object
    tweets_list = [[tweet.created_at, tweet.id, tweet.text] for tweet in tweets]
    
    # Creation of dataframe from tweets list
    # Add or remove columns as you remove tweet information
    tweets_df = pd.DataFrame(tweets_list)
  
  except BaseException as e:
        print('failed on_status,',str(e))
        time.sleep(3)
        
  print(tweets_df)

  #Get text contents of last tweet
  last_tweet = tweets_df.iat[0,2]   
  last_tweet_lower = last_tweet.lower()
  print('Tweet:' + last_tweet)
  

  ####################ORDERS######################
  #Define functions
  def buy(last_tweet):
    import os
    from alpaca_trade_api.rest import REST, TimeFrame
    #Determine if call or put

    #Authenticate Alpaca API
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    api = REST('API-KEY', 'SECRET-API-KEY', api_version='v2')

    #Configure trade parameters
    account = api.get_account()
    buying_power = account.buying_power
    buying_power = float(buying_power)
    size = 0.1 * buying_power #Max size you are willing to incur per position, this is set to 10%

    #Find ticker from tweet
    last_tweet_lower = last_tweet.lower()
    
    if '$' in last_tweet_lower:  #If $ in tweet then the ticker is usually following it
      import re
      pattern = r'(?<=\$)(.*?)(?= )'
      ticker = re.findall(pattern, last_tweet_lower)
      ticker = ticker[0]
      ticker = ticker.upper()

    #Else match ticker against a list of available tickers
    else:
      active_assets = api.list_assets(status='active')
      stocks = []
      for asset in active_assets:
        raw = vars(asset)
        dicts = raw['_raw']
        symbol = dicts['symbol']
        symbol = symbol.lower
        stocks.append(symbol)
      if any(word in last_tweet_lower for stock in stocks):
        ticker = stock.upper()
      else:
        #logging.warning('Could not locate a ticker within the tweet. Exiting...')
        print('Could not locate a ticker within the tweet. Exiting...')
        sys.exit()
    
    if 'p ' in last_tweet_lower:
      order_side = 'sell'
    else:
      order_side = 'buy'

    #Crosscheck portfolio for existing positions
    portfolio = api.list_positions()
    symbols = []
    for position in portfolio:
      symbol = position.symbol
      symbols.append(symbol)

    print('Ticker:' + ticker)

    #get position size
    quote = api.get_last_quote(ticker)
    quote = float(quote.askprice)
    size = int(size/quote)

    if ticker in symbols:
      print('Already have a position.')
      position = api.get_position(ticker)
      equity = abs(float(position.avg_entry_price)*float(position.qty))
      max_size = 0.125 * buying_power
      #Determine if already added
      if equity > max_size:
        print('Position already excedes max size, exiting...')
        sys.exit()
      else:
        adding = ['added', 'add', 'average down', 'averaged down']
        if any(word in last_tweet_lower for word in adding):
          print('This is an add, adding...')
          #logging.warning('This is an add, adding...')
          size = size/3
        else:  
          #logging.warning('Position already held, exiting...')
          print('Position already held, exiting...')
          sys.exit()
    else:
      pass

    #Submit the order
    api.submit_order(
      symbol=ticker,
      qty=size,
      side=order_side,
      type='market',
      time_in_force='gtc')
    mail_content = 'Opening {} shares in {}. Tweet: {}'.format(str(size), ticker, last_tweet)
    time.sleep(5)

    position=api.get_position(ticker)
    position = vars(position)
    position = position['_raw']
    avg = position['avg_entry_price']
    avg = float(avg) #average entry price

    #submit the stop-loss order
    if order_side == 'buy':
      api.submit_order(
        symbol=ticker,
        qty=size,
        side='sell',
        type='stop',
        stop_price=0.97*avg,
        time_in_force='gtc')
    else:
      api.submit_order(
        symbol=ticker,
        qty=size,
        side='buy',
        type='stop',
        stop_price=1.03*avg,
        time_in_force='gtc')
    return mail_content
  
  def sell(last_tweet):
    import os
    from alpaca_trade_api.rest import REST, TimeFrame

    #Authenticate Alpaca API
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    api = REST('PK697VVFFZMKBQ9A2JI3', 'fnuMYsPshafJDN5c7WTrhIt8yojaGMcFqh3DV4Lg', api_version='v2')

    #Configure trade parameters
    portfolio = api.list_positions()
    symbols = []
    for position in portfolio:
      name = position.symbol
      name = name.lower()
      symbols.append(name)

    #Find ticker from tweet
    last_tweet_lower = last_tweet.lower()

    #Match ticker against position
    if any(word in last_tweet_lower for symbol in symbols):
      ticker = symbol.upper()
      closed_orders = api.list_orders(
        status='closed',
        limit=1,
        nested=True)
      for order in closed_orders:
          order = vars(order)
          order = order['_raw']
          side = order['side']
          shares = order['filled_qty']
    else:
      closed_orders = api.list_orders(
        status='closed',
        limit=1,
        nested=True)
      for order in closed_orders:
        try:
          order = vars(order)
          order = order['_raw']
          side = order['side']
          ticker = order['symbol']
          ticker = ticker.upper()
          shares = order['filled_qty']
        except BaseException as e:
          #send email here
          print('Could not find a position matching the sell signal, check positions, exiting...')
          #logging.warning('Could not find a position matching the sell signal, check positions, exiting...')
          sys.exit()

    #Find stop-loss order and cancel it
    open_orders = api.list_orders(
      status='open',
      limit=3,
      nested=True)
    for order in open_orders:
      order = vars(order)
      order = order['_raw']
      stop_symbol = order['symbol']
      order_id = order['id']
      if ticker == stop_symbol:
        api.cancel_order(order_id)
      else:
        pass

    #Find position size
    position=api.get_position(ticker)
    position = vars(position)
    position = position['_raw']
    shares = position['qty']
    shares = int(shares)

    #exit partial position
    scale = ['1/2', '1/3', '2/3', 'out half']
    if any(word in last_tweet_lower for word in scale):
      print('This is a scale out, selling...')
      #logging.warning('This is a scale out, selling...')

      #if closing 1/2 position
      if word == '1/2' or 'out half': 
        if shares > 0:
          api.submit_order(
            symbol=ticker,
            qty=int(shares/2),
            side='sell',
            type='market',
            time_in_force='gtc')
          print('success')
          mail_content = 'Selling to close 1/2 of {}. Tweet: {}'.format(ticker, last_tweet)
        else:
          api.submit_order(
            symbol=ticker,
            qty=int(shares/2),
            side='buy',
            type='market',
            time_in_force='gtc')
          print('success')
          mail_content = 'Buying to close 1/2 of {}. Tweet: {}'.format(ticker, last_tweet)

      #if closing 1/3 position
      else: 
        if shares > 0:
          api.submit_order(
            symbol=ticker,
            qty=int(shares/3),
            side='sell',
            type='market',
            time_in_force='gtc')
          print('success')
          mail_content = 'Selling to close 1/3 of {}. Tweet: {}'.format(ticker, last_tweet)
        else:
          api.submit_order(
            symbol=ticker,
            qty=int(shares/3),
            side='buy',
            type='market',
            time_in_force='gtc')
          print('success')
          mail_content = 'Buying to close 1/3 of {}. Tweet: {}'.format(ticker, last_tweet)

    #if closing full position
    else: 
      if shares > 0:
        api.submit_order(
          symbol=ticker,
          qty=shares,
          side='sell',
          type='market',
          time_in_force='gtc')
        print('success')
        mail_content = 'Selling to close all of {}. Tweet: {}'.format(ticker, last_tweet)
      else:
        api.submit_order(
          symbol=ticker,
          qty=shares,
          side='buy',
          type='market',
          time_in_force='gtc')
        print('success')
        mail_content = 'Buying to close all of {}. Tweet: {}'.format(ticker, last_tweet)
    return mail_content

  adds = []
  sells = []

  buys_sells = adds.append(sells)

  if any(word in last_tweet_lower for word in adds):
    mail_content = buy(last_tweet)
  elif any(word in last_tweet_lower for word in sells):
    mail_content = sell(last_tweet)
  elif not any(word in last_tweet_lower for word in buys_sells):
    print('Not a buy or sell tweet, exiting')
    #logging.warning('Not a buy or sell tweet, exiting')


  # The body and the attachments for the mail
  message.attach(MIMEText(mail_content, 'plain'))

  # Create SMTP session for sending the mail
  session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
  session.starttls()  # enable security

  # login with mail_id and password
  session.login(sender_address, sender_pass)
  text = message.as_string()
  session.sendmail(sender_address, receiver_address, text)
  session.quit()

  done = 'Mail Sent'

  return done
