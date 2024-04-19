#region imports
from AlgorithmImports import *
#endregion

class IYMUniverseSelectionModel(ETFConstituentsUniverseSelectionModel):
    def __init__(self, universe_settings: UniverseSettings = None) -> None:
        # Select the QQQ ETF constituents to get correlated assets
        symbol = Symbol.Create("QQQ", SecurityType.Equity, Market.USA)
        super().__init__(symbol, universe_settings, self.ETFConstituentsFilter)

    def ETFConstituentsFilter(self, constituents: List[ETFConstituentData]) -> List[Symbol]:
        # Choose the top 1 security with the largest weight in the index to reduce slippage and keep speed of the algorithm
        selected = sorted([c for c in constituents if c.Weight],
                          key=lambda c: c.Weight, reverse=True)
        return [selected[0].Symbol]  # Only return the top 1 symbol
