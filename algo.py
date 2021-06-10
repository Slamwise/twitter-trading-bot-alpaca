import sys
import pymongo
import dns
#import logging

def tt3algo(self):
  ####################EMAILS######################
  import smtplib
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText

  # The mail addresses and password
  sender_address = 'jasperbot.t3@gmail.com'
  sender_pass = 'L3aF.09210'
  receiver_address = 'jasperbot.t3@gmail.com'

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
  consumer_key = "zfSUJduOLq0MOX0xtFMUyTott"
  consumer_secret = "M2oiB5bNekdUYDnDOQcIQ5Jz2VRiSjZxTEW55h376cMfbA3fjo"
  access_token = "881877178572566528-7NPh026TleuetNPnAyf0Na9yduxfdQX"
  access_token_secret = "FbpTXnD89Y9oBSKHSWnr6HAzgdmaHIQn22CfA2NugHd1M"

  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(access_token, access_token_secret)
  api = tweepy.API(auth,wait_on_rate_limit=True)

  #Get tweets
  username = 'TT3Private'
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
        
  #print(tweets_df)

  #Get text contents of Tom's last tweet
  last_tweet = tweets_df.iat[0,2]  
  last_tweet_lower = last_tweet.lower()
  print('Tweet:' + last_tweet)
  #print(last_tweet_lower)  

  ####################ORDERS######################
  #Define functions
  def buy(last_tweet):
    import os
    from alpaca_trade_api.rest import REST, TimeFrame
    #Determine if call or put

    #Authenticate Alpaca API
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    api = REST('PKIEK06P27I3AMCGED1K', 'jmo5LjOsnRI3Smzwpy216dNhcxUWx2NMkmYQ7NiR', api_version='v2')

    #Configure trade parameters
    account = api.get_account()
    buying_power = account.buying_power
    buying_power = float(buying_power)
    size = 0.08 * buying_power


    #Determine if OPEX week
    import datetime
    from datetime import date
    today = datetime.date.today()
    today = str(today)
    today = today[-2:]
    weekday = date.today().weekday()
    today = int(today)
    x = 4 - weekday
    friday = today + x
    if 15 < friday < 22:
      size = size*2/3
    else:
      pass
    
    #Find ticker from tweet
    last_tweet_lower = last_tweet.lower()
    #If $ in tweet then the ticker is usually following it
    if '$' in last_tweet_lower:
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
        stocks.append(symbol)

      words = last_tweet.split()
      for word in words:
        for stock in stocks:
          if word == stock:
            ticker = word
      if ticker is not None:
        print('Ticker is: {}'.format(ticker))
      else:
        print('No ticker identified within tweet, exiting.')
        mail_content = 'Buy tweet but could not identify ticker. Tweet: {}'.format(last_tweet)
        return mail_content
    
    tweet_no_ticker = last_tweet_lower.replace(ticker.lower(), '')
    if 'p ' in tweet_no_ticker:
      order_side = 'sell'
    else:
      order_side = 'buy'

    #Crosscheck portfolio for existing positions
    portfolio = api.list_positions()
    symbols = []
    for position in portfolio:
      symbol = position.symbol
      symbols.append(symbol)

    #get position size
    quote = api.get_last_quote(ticker)
    quote = float(quote.askprice)
    size = int(size/quote) #convert dollar size to shares

    if ticker in symbols:
      print('Already have a position.')
      position = api.get_position(ticker)
      equity = abs(float(position.avg_entry_price)*float(position.qty))
      max_size = 0.125 * buying_power
      #Determine if already added
      if equity > max_size:
        print('Position already excedes max size, exiting...')
        mail_content = None
        return mail_content
      else:
        adding = ['added', 'add', 'average down', 'averaged down']
        if any(word in last_tweet_lower.split() for word in adding):
          print('This is an add, adding...')
          #logging.warning('This is an add, adding...')
          size = int(size/3)
        else:  
          #logging.warning('Position already held, exiting...')
          print('Position already held, exiting...')
          mail_content = None
          return mail_content
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
        type='limit',
        order_class='oco',
        stop_loss={'stop_price': str(avg * 0.985)},
        take_profit={'limit_price': str(avg * 1.03)},
        time_in_force='gtc')
    else:
      api.submit_order(
        symbol=ticker,
        qty=abs(size),
        side='buy',
        type='limit',
        order_class='oco',
        stop_loss={'stop_price': str(avg * 1.015)},
        take_profit={'limit_price': str(avg * 0.97)},
        time_in_force='gtc')
    return mail_content

  def sell(last_tweet):
    import os
    from alpaca_trade_api.rest import REST, TimeFrame

    #Authenticate Alpaca API
    os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'
    api = REST('PKIEK06P27I3AMCGED1K', 'jmo5LjOsnRI3Smzwpy216dNhcxUWx2NMkmYQ7NiR', api_version='v2')

    #Configure trade parameters
    portfolio = api.list_positions()
    symbols = []
    for position in portfolio:
      name = position.symbol
      name = name.lower()
      symbols.append(name)

    #Find ticker from tweet
    last_tweet_lower = last_tweet.lower()

    words = last_tweet_lower.split()
    for word in words:
        for stock in symbols:
          if word == stock.lower():
            ticker = word.upper()
    if ticker is not None:
      print('Ticker is: {}'.format(ticker))
    #Match ticker against position
    else:
      active_assets = api.list_assets(status='active')
      stocks = []
      for asset in active_assets:
        symbol = asset.symbol
        stocks.append(symbol)
      words = last_tweet.split()
      for word in words:
        for stock in stocks:
          if word == stock:
            ticker = word
      if ticker is not None:
        print('Ticker is: {}'.format(ticker))
      else:
        num_positions = len(portfolio)
        if len(portfolio) == 1:
          for position in portfolio:
            shares = int(float(position.qty))
            ticker = position.symbol
        else:
          print('No ticker identified within tweet, exiting.')
          mail_content = 'Sell tweet but no ticker found, either ticker not specified in tweet or position not held. Tweet: {}'.format(last_tweet)
          return mail_content
    
    #Find stop-loss order and cancel it
    open_orders = api.list_orders(
      status='open',
      limit=5,
      nested=True)
    for order in open_orders:
      order = vars(order)
      order = order['_raw']
      stop_symbol = order['symbol']
      order_id = order['id']
      if ticker == stop_symbol:
        api.cancel_order(order_id)
        time.sleep(3)
      else:
        pass

    #Find position size
    position=api.get_position(ticker)
    position = vars(position)
    position = position['_raw']
    shares = position['qty']
    shares = int(float(shares))

    #exit partial position
    scale = ['1/2', '1/3', '2/3', 'half']
    s = next((word for word in last_tweet_lower.split() if word in scale), None)
    if s:
      print('This is a scale out, selling...')
      print('scale out word: {}'.format(s))
      #logging.warning('This is a scale out, selling...')

      #if closing 1/2 position
      if s == '1/2' or s == 'half': 
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
            qty=abs(int(shares/2)),
            side='buy',
            type='market',
            time_in_force='gtc')
          print('success')
          mail_content = 'Buying to close 1/2 of {}. Tweet: {}'.format(ticker, last_tweet)

      #if closing 1/3 position
      elif s == '1/3' or s == '2/3': 
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
            qty=abs(int(shares/3)),
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
          qty=abs(shares),
          side='buy',
          type='market',
          time_in_force='gtc')
        print('success')
        mail_content = 'Buying to close all of {}. Tweet: {}'.format(ticker, last_tweet)
    return mail_content

  def Sort(last_tweet, tweets_df):
    ####################MONGODB######################
    last_tweet_lower = last_tweet.lower
    tweet = tweets_df.iat[0,2]
    tweet_time = tweets_df.iat[0,0]

    client = pymongo.MongoClient("mongodb+srv://smsa2222:zekerdog@cluster0.pkt6x.mongodb.net/myFirstDatabase?retryWrites=true&w=majority", authSource='admin')
    db = client.db0
    tweets = db.tweets0

    #Deterimine if algo has already read the current tweet
    cur = tweets.find().sort("_id", -1).limit(1) #last addition to mongodb
    for doc in cur:
      last_tweet_db = doc['tweet']
    if tweet == last_tweet_db: #not a new tweet, exit
      print('they are the same')
      mail_content = None
      return mail_content

    else: #new tweet, decide what to do with it 
      data = {'time': tweet_time, 'tweet': tweet}
      tweets.insert_one(data)
      if last_tweet[0] == '@':
        print('This is a reply, not a buy or sell tweet.')
        mail_content = None
        return mail_content
        
      adds = ['#tt3lotto', '#tt3alert', 'added', 'in', 'bot', 'bought', '#tt3alerts', '#tt3lottos']
      sells = ['out', 'sold', '1/2', '1/3', '2/3', 'cutting', 'cut']

      buys_sells = []
      for word in adds:
        buys_sells.append(word)
      for word in sells:
        buys_sells.append(word)

      if any(word in last_tweet_lower.split() for word in adds):
        print('Type: buy tweet')
        mail_content = buy(last_tweet)
        return mail_content
      elif any(word in last_tweet_lower.split() for word in sells):
        if 'break' in last_tweet_lower.split() or 'breaking' in last_tweet_lower.split():
          print('Break out tweet, not a buy or sell tweet. Exiting...')
          mail_content = None
          return mail_content
        else:
          print('Type: sell tweet')
          mail_content = sell(last_tweet)
          return mail_content
      elif not any(word in last_tweet_lower.split() for word in buys_sells):
        print('Not a buy or sell tweet, exiting')
        mail_content = None
        return mail_content

  mail_content = Sort(last_tweet, tweets_df)

  if mail_content is not None:
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

  else:
    done = 'Done'

  return done
