import discord
from discord.ext import commands
import asyncio
from yfinance import download
from requests import get
from time import time
from pandas import DataFrame, to_datetime, concat
from datetime import datetime
from math import floor
from agent import AGENT
import os
from yfinance import download
from datetime import datetime, timedelta

client = discord.Client()
SESSION = True
Last_update = datetime.fromtimestamp(time()).strftime("%H:%M:%S")
Last_minute = -1
Agent = AGENT()

# id canali
generaleCH = 1005242726125678635
attivitaCH = 1005245873883713546
datiCH = 1005255394710528162
transazioniCH = 1005968395927293962
azioniCH = 1005245915931615393
bookCH = 1017463347026858134
spamCH = 1022115220031811685

# statistiche varie
bookValues = []
ohlc = []

def check_time():
	global Last_update
	now = datetime.fromtimestamp(time()).strftime("%H:%M:%S").split(":")
	soglia = Last_update.split(":")
	now = [int(i) for i in now]
	soglia = [int(i) for i in soglia]
	if soglia[1] >= 55:
		soglia[1] = -5
		soglia[0] = (soglia[0]+1)%24
	else:
		soglia[1] = floor(soglia[1]/5)*5

	if now[0] >= soglia[0] and now[1] >= soglia[1]+5 and now[2]>20:
		Last_update = datetime.fromtimestamp(time()).strftime("%H:%M:%S")
		return True

	return False

def check_book_time():
	global Last_minute
	now = datetime.fromtimestamp(time()).strftime("%H:%M:%S").split(":")
	now = int(now[1])
	if (Last_minute+1)%60 <= now:
		Last_minute = now
		return True
	return False

def get_data(asset):
	global ohlc
	SPAN = 500 # < 720

	"""resp0 = get(f'https://api.binance.com/api/v3/klines?symbol={asset[0]}BUSD&interval=5m&limit={SPAN}')
	data0 = DataFrame(resp0.json()).rename(columns={0:"Datetime",1:"Open",2:"High",3:"Low",4:"Close",5:"Volume",8:"Trades"})
	data0["Datetime"] = data0["Datetime"]//1000 # in secondi
	data0 = data0.set_index("Datetime").sort_index()
	
	if type(ohlc) == type([]):
		ohlc = data0
	else:
		ohlc = concat([ohlc, data0]).drop_duplicates(keep='first')
		ohlc = ohlc.sort_index()
	"""
	data0 = download("ETH-USD", start=datetime.now()-timedelta(hours=40), end=datetime.now(), interval="5m", auto_adjust=False, prepost=False).astype(float).sort_index()

	return [data0]

def avg(v):
	return sum(v)/len(v)

def std(v):
	if len(v)<=1:
		return -1
	medio = avg(v)
	return pow( sum([(i-medio)**2 for i in v])/(len(v)-1) ,0.5)

def getBook():
	book = "https://api.binance.com/api/v3/depth?symbol=ETHBUSD&limit=15"
	return get(book).json()

def printBookStatistics():
	global bookValues
	book = getBook()
	asksSell = book['asks']
	bidsBuy = book['bids']

	quantitySell = [float(i[1]) for i in asksSell]
	quantityBuy = [float(i[1]) for i in bidsBuy]
	priceSell = [float(i[0]) for i in asksSell]
	priceBuy = [float(i[0]) for i in bidsBuy]

	sommaSell = round(sum(quantitySell),2)
	sommaBuy = round(sum(quantityBuy),2)

	SellStd = round(std(priceSell),3)
	BuysStd = round(std(priceBuy),3)

	a = ",".join( [f"[{i[0]},{i[1]}]" for i in asksSell])
	b = ",".join( [f"[{i[0]},{i[1]}]" for i in bidsBuy])
	bookValues.append([sommaSell,sommaBuy,SellStd,BuysStd,Agent.get_price(),time()])
	return f"asksSell:{a}\nbidsBuy:{b}\n{sommaSell}, {sommaBuy}, {SellStd}, {BuysStd}"

def process_data(data):
	if not Agent.dentro:
		return Agent.buy(datetime.fromtimestamp(time()).strftime("%H:%M:%S"), data)
	else:
		return Agent.sell(datetime.fromtimestamp(time()).strftime("%H:%M:%S"), data)


@client.event
async def on_ready():
	for guild in client.guilds:

		print(
			f'{client.user} is connected to the following guild:\n'
			f'{guild.name}(id: {guild.id})'
		)


	await client.get_channel(attivitaCH).send("Starting Connection.")
	global SESSION
	while True:
		if SESSION==True:
			try:
				await asyncio.sleep(15)
				if check_book_time():
					await client.get_channel(bookCH).send(printBookStatistics())
				if check_time():
					now = datetime.fromtimestamp(time()).strftime("%H:%M")
					await client.get_channel(attivitaCH).send(f"Connection check({now}).")
					data = get_data(Agent.currentName)
					info0 = data[0].iloc[-1]
					await client.get_channel(datiCH).send(f"{Agent.currentName[0]}:{info0.name}| Open:{info0['Open']}/Low:{info0['Low']}/High:{info0['High']}/Close:{info0['Close']}")
					flag, r = process_data(data)
					if flag:
						await client.get_channel(transazioniCH).send(r)	
						allowed_mentions = discord.AllowedMentions(everyone = True)
						await client.get_channel(azioniCH).send(content="@everyone Stock transaction happened.", allowed_mentions=allowed_mentions)
						r = Agent.get_current_state(get_data(Agent.currentName))
						await client.get_channel(azioniCH).send(r)
					
			except Exception as e:
				print(e)
				allowed_mentions = discord.AllowedMentions(everyone = True)
				await client.get_channel(azioniCH).send(content=str(e), allowed_mentions=allowed_mentions)

		elif SESSION==False:
			try:
				await asyncio.sleep(100)
			except Exception as e:
				print(e)
		elif SESSION==-1:
			break


@client.event
async def on_message(message):
	global SESSION
	global ohlc
	if message.author == client.user:
		return

	if message.channel.id==azioniCH:
		if message.content=="shutdown" or message.content=="s":
			SESSION = not SESSION
			await message.channel.send(f"Execution is now set to {SESSION}")
		elif message.content=="ss":
			SESSION = -1
			await client.close()
		elif message.content=="help" or message.content=="h":
			await message.channel.send(f"help-h\nversion-v\nshutdown/execute-s\nbalance-b\nstate-c\nforce buy 0\nforce sell\nbook\nenter/exit e")
		elif message.content=="version" or message.content=="v":
			await message.channel.send(f"B1.1.3")
		elif message.content=="enter" or message.content=="exit" or message.content=="e":
			Agent.dentro = not Agent.dentro
			await message.channel.send(f"Stato corrente aggiornato: dentro={Agent.dentro}")
		elif message.content=="balance" or message.content=="b":
			await message.channel.send(Agent.get_total_balance())
		elif message.content=="state" or message.content=="c": # c di current state
			r = Agent.get_current_state(get_data(Agent.currentName))
			await message.channel.send(r)
		elif "force buy 0" in message.content:
			if len(message.content.split(" "))<3:
				await client.get_channel(azioniCH).send(f"Specificare quale comprare[0,1]: {Agent.currentName}")
			else:
				if len(message.content.split(" "))==3:
					flag, r = Agent.buy(datetime.fromtimestamp(time()).strftime("%H:%M:%S"),get_data(Agent.currentName),True,int(message.content.split(" ")[2]))
					if flag:
						await client.get_channel(transazioniCH).send(r)
				elif len(message.content.split(" "))==4:
					flag, r = Agent.buy(datetime.fromtimestamp(time()).strftime("%H:%M:%S"),get_data(Agent.currentName),True,int(message.content.split(" ")[2]),True)
					if flag:
						await client.get_channel(transazioniCH).send(r)
		elif message.content=="force sell":
			flag, r = Agent.sell(datetime.fromtimestamp(time()).strftime("%H:%M:%S"),get_data(Agent.currentName),True)
			if flag:
				await client.get_channel(transazioniCH).send(r)
	elif message.channel.id==spamCH:
		if message.content=="book":
			m = "["+",".join( [f"[{i[0]},{i[1]},{i[2]},{i[3]},{i[4]},{i[5]}]" for i in bookValues])+"]"
			for i in range(0,len(m),1995):
				await message.channel.send(m[i:i+1995])
		if message.content=="ohlc":
			m = ohlc[["Open","High","Low","Close","Volume"]].astype(float).round(2).to_string(index=True).split("\n")
			for i in range(0,len(m),10):
				await message.channel.send("\n".join(m[i:i+10]))
	else:
		#print(message.channel.id)
		allowed_mentions = discord.AllowedMentions(everyone = True)
		await message.channel.send(content="@everyone owo", allowed_mentions=allowed_mentions)

client.run(os.environ['DISCORD_TOKEN'])
