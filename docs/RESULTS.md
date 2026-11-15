# Strategy test results

The **Compare strategies** workflow produced these results on 15 Nov 2026. Re-run it any time from the Actions tab.

## How we tested (and tried not to fool ourselves)

- **16 markets:**
  - Stocks: AAPL, MSFT, AMZN, JPM, XOM
  - Index ETFs: SPY, QQQ, IWM, EFA, EWU
  - Crypto: BTC, ETH
  - Forex: EUR/USD, GBP/USD, USD/JPY
  - Gold: GLD
- **Data:** up to 25 years of daily closes, with dividends included.
- **Trading rules:** each signal is acted on at the **next** day's close, and every trade pays a 0.1% fee. Money is assumed to earn nothing while out of the market. In reality, cash earns interest, which would slightly help the strategies.
- **Training period (2001–2020):** used to choose the strategy. The highest median Sharpe ratio (return per unit of risk) won.
- **Test period (2021–Nov 2026):** data the choice never saw. This is the honest check.

The numbers below are medians across the 16 markets.

## Training period (2001–2020): picking the winner

| Strategy | Yearly return | Sharpe | Worst drop | Beat B&H on Sharpe |
|---|---|---|---|---|
| **200-day trend rule (3% buffer)** ← chosen | 7.4% | **0.55** | **−38%** | 9/16 |
| Trend + dip buying | 7.2% | 0.54 | −38% | 8/16 |
| *Buy & hold* | *9.2%* | *0.51* | *−60%* | – |
| Original 4-indicator score | 7.1% | 0.46 | −46% | 7/16 |
| 12-month momentum | 6.1% | 0.45 | −39% | 5/16 |
| 200-day trend rule (no buffer) | 5.5% | 0.44 | −37% | 9/16 |
| Golden cross | 6.6% | 0.43 | −46% | 8/16 |
| Breakout (55/20) | 3.2% | 0.36 | −32% | 3/16 |
| Short-term dip buying | 1.0% | 0.17 | −22% | 1/16 |

## Test period (2021–2026): unseen data

| Strategy | Yearly return | Sharpe | Worst drop | Smaller drop than B&H |
|---|---|---|---|---|
| *Buy & hold* | ***13.4%*** | ***0.71*** | *−31%* | – |
| Trend + dip buying | 9.0% | 0.67 | −27% | 13/16 |
| **200-day trend rule (3% buffer)** | 9.0% | 0.66 | **−26%** | 12/16 |
| 200-day trend rule (no buffer) | 9.5% | 0.62 | −27% | 14/16 |
| Golden cross | 8.3% | 0.54 | −25% | 13/16 |
| 12-month momentum | 7.4% | 0.52 | −27% | 12/16 |
| Original 4-indicator score | 7.0% | 0.50 | −24% | 13/16 |
| Breakout (55/20) | 4.6% | 0.47 | −20% | 15/16 |
| Short-term dip buying | 1.8% | 0.26 | −13% | 16/16 |

## What this means

1. **Nothing beat buy & hold on return.** That's normal: most simple timing rules don't. Anyone selling signals that "beat the market" should be able to show results like this, and usually can't.
2. **The 200-day trend rule did its real job, which is cutting crashes.** In 2001–2020, which includes the 2008 crash, its typical worst drop was −38% against −60% for buy & hold, and its return per unit of risk was higher. In the 2021–2026 test, it gave up some return in exchange for slightly smaller drops.
3. **It replaced the original strategy.** The original 4-indicator score did worse on both periods.
4. **Forex is a weak spot.** Every strategy scored around zero on currency pairs. Think twice before trading forex on these signals.

**Who this suits:** people who would otherwise panic-sell in a crash, or who want a clear, rule-based "get out" signal. **Who it doesn't suit:** anyone hoping to beat the market.
