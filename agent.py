from numpy import arctan
from ta.trend import *
from ta.momentum import *
from ta.volatility import *
from algorithmETH import AlgorithmETH
from time import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from json import dumps,loads
from time import sleep, time
import pandas as pd
from binance.spot import Spot
import os

class AGENT:
	def __init__(self):
		# dati api
		self.api_key = os.environ['API_KEY']
		self.api_sec = os.environ['API_SEC']
		self.client = Spot(key=self.api_key, secret=self.api_sec)

		# parametri
		self.tassa = 0.0
		self.moltiplicatore = 1
		self.invest = 1 # 100%

		# algoritmi
		self.ETH = AlgorithmETH(self.tassa,self.moltiplicatore)
		self.A = [self.ETH]

		# Parametri della simulazione
		self.staticMoney = 10
		self.staticETH = 0.0003

		self.strategia = "-"
		self.current = -1
		self.currentName = ["ETH"]
		self.currentNameResult = ["ETH"]

		self.money = 0
		self.stocks = 0
		self.euro = 0
		self.get_balance()
		self.dentro = False
		self.entrata = 0
		self.ora = 0
		self.shorting = False

	# ========================= funzioni di gestione ========================= #
	def buy(self, now, data, forced=False, which=-1, short=False):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		if (not self.dentro and self.A[0].check_buy(-1) == True):
			self.current = 0
			self.ora = int((time()-60)*1000)
			self.get_balance()
			spesa = self.invest*self.money

			if "short" not in self.A[0].strategia:
				output = self.buy_order(0)
			elif "short" in self.A[0].strategia:
				self.shorting = True
				output = self.sell_order(0)

			k = 0
			while k<8:
				sleep(10)
				flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
				if flag:
					self.entrata = price
					break
				k += 1

			if costo!=0:
				self.dentro = True
			self.get_balance()
			return [True,f"Buy: Crypto:{self.stocks} {self.currentName[self.current]}({costo}*{self.moltiplicatore}={costo*self.moltiplicatore}$) / Balance:{self.money}$ || {output}"]

		elif forced:
			self.current = which
			self.ora = int((time()-60)*1000)
			self.get_balance()
			spesa = self.invest*self.money
			if short==False:
				output = self.buy_order(0)
			elif short==True:
				self.shorting = True
				output = self.sell_order(0)

			print(output)
			k = 0
			while k<8:
				sleep(10)
				flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
				print(flag,costo,tassa,price)
				if flag:
					self.entrata = price
					break
				k += 1
			if costo!=0:
				self.dentro = True
			self.get_balance()
			return [True,f"Buy: Crypto:{self.stocks} {self.currentName[self.current]}({costo}*{self.moltiplicatore}={costo*self.moltiplicatore}$) / Balance:{self.money}$ || {output}"]
		return [False,""]

	def sell(self, now, data, forced=False):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		if (self.dentro and self.A[self.current].check_sell(-1, self.entrata) == True) or forced:
			self.dentro = False
			if self.shorting==True or "short" in self.A[0].strategia:
				output = self.buy_order(0)
				self.shorting = False
			else:
				output = self.sell_order(0)

			sleep(10)
			self.get_balance()

			m = self.current
			self.current = -1
			return [True,f"Sell: Crypto:{self.stocks} {self.currentName[m]} / Balance:{round(self.money,2)}$ || {output}"]
		return [False,""]

	def get_total_balance(self):
		self.get_balance()
		return f"Balance: {self.money}$+({self.staticMoney}$) / Crypto: {self.stocks}{self.currentName[self.current]}({self.get_price()*self.stocks}$)({self.get_price()}ETH/$) / Total(ETH+BUSD): {self.money+self.get_price()*self.stocks}$ /Homecash: {self.euro}€"


	def get_current_state(self, data):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		return f"{self.currentName[0]}: EMAb={round(self.A[0].df[f'EMA{self.A[0].periodiB}'].iloc[-1],2)} / EMAl={round(self.A[0].df[f'EMA{self.A[0].periodiL}'].iloc[-1],2)} / Psar>={self.A[0].df['psar_di'].iloc[-1]} / Aroon={round(self.A[0].df['aroon_indicator'].iloc[-1],2)} / ROC={round(self.A[0].df['rocM'].iloc[-1],2)}"


	# ========================= funzioni di richiesta ========================= #	
	def get_price(self):
		return float(requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={self.currentName[0]}BUSD').json()["price"])

	def get_balance(self):
		params = {
			'recvWindow': 60000
		}
		v = self.client.account(**params)["balances"]
		money = 0
		stocks= 0
		for i in v:
			if i["asset"] == "ETH":
				stocks = float(i["free"])-self.staticETH
			if i["asset"] == "BUSD":
				money = float(i["free"])-self.staticMoney
			if i["asset"] == "EUR":
				self.euro = float(i["free"])
		self.money = money
		self.stocks = stocks
		return money,stocks

	def get_trade_history(self, ora):
		params = {
			'symbol': 'ETHBUSD',
			'recvWindow': 60000
		}
		v = self.client.my_trades(**params)
		df = pd.DataFrame(v)
		if not df.empty:
			df = df.loc[df["time"]>ora].set_index("time").sort_index(ascending=False)
			costo = df["quoteQty"].astype(float).sum()
			tassa = df["commission"].astype(float).sum()
			volume = df["qty"].astype(float).sum()
			price = df["price"].astype(float).mean()
			return True,costo,tassa,price,volume
		else:
			return False,0,0,0,0

	def get_volume(self):
		flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
		return volume

	def buy_order(self, asset):
		print(f"{self.currentNameResult[asset]}EUR")
		self.get_balance()

		if self.shorting==True or "short" in self.A[0].strategia:
			params = {
				'symbol': 'ETHBUSD',
				'side': 'BUY',
				'type': 'MARKET',
				'quoteOrderQty': round(self.money/2,2),
				'recvWindow': 60000
			}
		else:
			params = {
				'symbol': 'ETHBUSD',
				'side': 'BUY',
				'type': 'MARKET',
				'quoteOrderQty': round(self.money,2),
				'recvWindow': 60000
			}

		v = self.client.new_order(**params)
		return v

	def sell_order(self, asset):
		print(f"{self.currentNameResult[asset]}EUR")
		self.get_balance()
		if self.shorting==True or "short" in self.A[0].strategia:
			params = {
				'symbol': 'ETHBUSD',
				'side': 'SELL',
				'type': 'MARKET',
				'quantity': round(self.stocks,5),
				'recvWindow': 60000
			}
		else:
			params = {
				'symbol': 'ETHBUSD',
				'side': 'SELL',
				'type': 'MARKET',
				'quantity': round(self.stocks,5),#/2
				'recvWindow': 60000
			}
		v = self.client.new_order(**params)
		return v
