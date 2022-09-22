from numpy import linspace, meshgrid, array, arctan
from ta.trend import *
from ta.momentum import *
from ta.volatility import *
import pandas as pd

class AlgorithmETH:
	def __init__(self, tassa, moltiplicatore):
		self.df = -1

		# parametri
		self.tassa = tassa
		self.moltiplicatore = moltiplicatore

		# stop calls
		self.stopWinMACD = self.tassa+0.1/self.moltiplicatore #
		self.stopLossMACD = (0.015)/self.moltiplicatore #
		self.stopWinMACDs = self.tassa+0.007/self.moltiplicatore
		self.stopLossMACDs = (0.000)/self.moltiplicatore
		self.stopWinBollinger = self.tassa+0.4/self.moltiplicatore
		self.stopLossBollinger = (0.01)/self.moltiplicatore

		# parametri periodi
		self.ADXperiodo = 14
		self.periodiB = 6
		self.periodiL = 66
		self.Periodo = 25
		self.longPeriod = 3*self.Periodo

		self.Breve = self.periodiB
		self.Lunga = self.periodiL

		self.strategia = "-"


	# ========================= funzioni dell'algoritmo ========================= #
	def check_buy(self, t):
		macd = self.df[f'EMA{self.Breve}'].iloc[t]>self.df[f'EMA{self.Lunga}'].iloc[t]
		aroonMACD = self.df['aroon_indicator'].iloc[t]>50
		sarM = self.df['psar_di'].iloc[t]==False
		
		Smacd = self.df[f'EMA{self.Breve}'].iloc[t]<self.df[f'EMA{self.Lunga}'].iloc[t]
		SrocMACD =  self.df['rocM'].iloc[t]<0.2
		SsarM = self.df['psar_di'].iloc[t]==True

		if macd and aroonMACD:
			if sarM:
				self.strategia = "MACD"
		elif Smacd and SrocMACD and False:
			if SsarM:
				self.short = True
				self.strategia = "MACDshort"
		return self.strategia != "-"

	def check_sell(self, t, entrata):
		if self.strategia == "MACD":
			if self.df[f'EMA{self.Breve}'].iloc[t]<self.df[f'EMA{self.Lunga}'].iloc[t] or self.stopCallMacd(t,entrata):
				self.strategia = "-"
		elif self.strategia == "MACDshort":
			if self.df[f'EMA{self.Breve}'].iloc[t]>self.df[f'EMA{self.Lunga}'].iloc[t] or self.stopCallMacdshort(t,entrata):
				self.strategia = "-"
		return self.strategia == "-"

	def stopCallMacd(self, t, entrata):
		sar = self.moltiplicatore*(self.df['Close'].iloc[t]*(1-self.tassa)-entrata)/entrata>=0 and self.df['psar_di'].iloc[t]==True
		upper = self.df['Close'].iloc[t]>entrata*(1+self.stopWinMACD)
		lower = self.df['Close'].iloc[t]<entrata*(1-self.stopLossMACD)
		return upper or lower or sar

	def stopCallMacdshort(self, t, entrata):
		sar = self.moltiplicatore*(self.df['Close'].iloc[t]*(1+self.tassa/2)-entrata*(1-self.tassa/2))/entrata<=0 and self.df['psar_di'].iloc[t]==False
		lower = self.df['Close'].iloc[t]<entrata*(1-self.stopWinMACDs)
		upper = self.df['Close'].iloc[t]>entrata*(1+self.stopLossMACDs)
		return upper or lower or sar

	def analyzeDf(self):
		# EMA
		self.df[f'EMA{self.periodiB}'] = ema_indicator(self.df['Close'], self.periodiB, False)
		self.df[f'EMA{self.periodiL}'] = ema_indicator(self.df['Close'], self.periodiL, False)

		# Parabolic SAR
		parabolicSar = PSARIndicator(self.df['High'],self.df['Low'],self.df['Close'])
		self.df['psar'] = parabolicSar.psar()
		self.df['psar_di'] = self.df['psar']>self.df['Close']

		# Aroon
		aroon = AroonIndicator(self.df['Close'])
		self.df['aroon_indicator'] = aroon.aroon_indicator()

		# roc
		rocM = ROCIndicator(self.df['Close'])
		self.df['rocM'] = rocM.roc()
		
