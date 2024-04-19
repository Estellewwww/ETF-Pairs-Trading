from universe import IYMUniverseSelectionModel
from AlgorithmImports import *
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import numpy as np

class PairsTradingAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 3, 1)
        self.SetEndDate(2024, 3, 1)
        self.SetCash(1000000)
        self.UniverseSettings.Resolution = Resolution.Minute

        self.mainSymbol = "QQQ"
        self.mainAsset = self.AddEquity(self.mainSymbol, Resolution.Minute)
        self.macdMainAsset = self.MACD(self.mainSymbol, 12, 26, 9, MovingAverageType.Simple, Resolution.Minute)

        self.pairETF = None
        self.macdIndicators = {}
        self.priceHistory = {self.mainSymbol: [], "pairETF": []}  # Initialize price history

        self.SetUniverseSelection(IYMUniverseSelectionModel())

    def OnSecuritiesChanged(self, changes):
        for added in changes.AddedSecurities:
            if added.Symbol.Value != self.mainSymbol:
                self.pairETF = added
                self.macdIndicators[added.Symbol] = self.MACD(added.Symbol, 12, 26, 9, MovingAverageType.Simple, Resolution.Minute)
                # Initialize the price history for the new ETF symbol
                self.priceHistory[added.Symbol] = []  # Start tracking price for co-integration
                break
        for removed in changes.RemovedSecurities:
            if removed.Symbol == self.pairETF.Symbol:
                # Clean up when the pair ETF is removed
                self.pairETF = None
                if removed.Symbol in self.macdIndicators:
                    del self.macdIndicators[removed.Symbol]
                if removed.Symbol in self.priceHistory:
                    del self.priceHistory[removed.Symbol]

    def UpdatePriceHistory(self, mainPrice, pairPrice):
        # Safely update the price history only if the pair ETF exists
        if self.pairETF and self.pairETF.Symbol in self.priceHistory:
            self.priceHistory[self.mainSymbol].append(mainPrice)
            self.priceHistory[self.pairETF.Symbol].append(pairPrice)
        else:
            self.Debug("No valid pair ETF selected or price history key does not exist")

    def OnData(self, data):
        if self.pairETF is None or not self.macdMainAsset.IsReady or not data.ContainsKey(self.mainSymbol):
            return
        
        if not data.ContainsKey(self.pairETF.Symbol) or not self.macdIndicators.get(self.pairETF.Symbol).IsReady:
            return

        self.UpdatePriceHistory(data[self.mainSymbol].Price, data[self.pairETF.Symbol].Price)
        
        if len(self.priceHistory[self.mainSymbol]) > 2000 and len(self.priceHistory.get(self.pairETF.Symbol, [])) > 2000:
            ci_factor = self.AnalyzeCoIntegration()
            if ci_factor:
                self.TradeBasedOnCoIntegration(ci_factor)

            macd_difference = self.macdMainAsset.Current.Value - self.macdIndicators[self.pairETF.Symbol].Current.Value
            if abs(macd_difference) > 0.5:
                allocation = self.CalculateAllocation(macd_difference)
                if macd_difference > 0:
                    self.SetHoldings(self.mainSymbol, allocation)
                    self.SetHoldings(self.pairETF.Symbol, -allocation)
                else:
                    self.SetHoldings(self.pairETF.Symbol, allocation)
                    self.SetHoldings(self.mainSymbol, -allocation)
            else:
                self.Liquidate(self.mainSymbol)
                self.Liquidate(self.pairETF.Symbol)

    def AnalyzeCoIntegration(self):
    # Ensure both arrays have the same length
        min_length = min(len(self.priceHistory[self.mainSymbol]), len(self.priceHistory[self.pairETF.Symbol]))
        main_prices = self.priceHistory[self.mainSymbol][-min_length:]
        pair_prices = self.priceHistory[self.pairETF.Symbol][-min_length:]

        if min_length > 0:
            prices_matrix = np.column_stack([main_prices, pair_prices])
            result = coint_johansen(prices_matrix, det_order=0, k_ar_diff=1)
            return result.lr1[0] > result.cvt[0, 0]  # Check if co-integration exists at the 5% level
        else:
            return False


    def TradeBasedOnCoIntegration(self, ci_factor):
        if ci_factor < -1.5:  # Simplified trading thresholds
            self.SetHoldings(self.mainSymbol, -0.5)
            self.SetHoldings(self.pairETF.Symbol, 0.5)
        elif ci_factor > 1.5:
            self.SetHoldings(self.mainSymbol, 0.5)
            self.SetHoldings(self.pairETF.Symbol, -0.5)

    def CalculateAllocation(self, macd_difference):
        return 0.5  # Fixed allocation for demonstration, adjust as needed

