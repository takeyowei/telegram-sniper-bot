# Telegram Sniper Bot — PAPER TRADING ONLY

> **⚠️ DEMO ONLY — NO REAL MONEY.**
> This bot trades **paper only**: balances are floats in "paper SOL",
> prices come from a seeded simulation, and every honeypot/rug check is
> **SIMULATED**. There is no wallet, no private key, no RPC endpoint and
> no real-money code path anywhere in this repo. Nothing here can move
> real funds, by design.

A Telegram bot that listens for token calls posted in a channel, parses
the token + buy size, runs simulated safety checks, and executes the
trade on a simulated market with a paper wallet — logging per-order
latency and tracking paper P&L per position. Built with
[python-telegram-bot](https://python-telegram-bot.org/); the parser,
market, trader and checks are pure Python and fully testable offline.

The pipeline, exactly as a real sniper bot needs it:

```
channel call -> parse token + size -> SIMULATED checks
             -> PASS / WARN: paper trade   |   BLOCK: skip, nothing traded
             -> latency log + paper P&L report
```

## Features

- **Call parsing** for SOL mints (base58, after `CA:`/`contract`/`mint`/
  `address` or standalone), EVM contracts (`0x` + 40 hex) and `$SYMBOL`,
  plus buy size (`buy 1.5 SOL`, `ape 0.5 SOL`, `amount: 2 SOL`).
- **SIMULATED honeypot/rug checks** (buy tax, sell tax, simulated sell
  test, liquidity flag) with a PASS / WARN / BLOCK verdict. BLOCK
  verdicts are never traded. Symbol-only calls (no contract to check)
  are skipped, never traded.
- **Paper market**: seeded random-walk prices, so the same seed always
  reproduces the same session — tests and the demo are deterministic.
- **Paper wallet**: starting balance 100 paper SOL, 0.25% simulated fee
  per side, size-dependent slippage (0.1% + 0.05% per paper SOL, capped
  at 2%).
- **Per-order latency log**: `processing_ms` is really measured
  (wall-clock of the local simulated execution), and
  `modeled_confirm_ms` is a *modelled* chain-confirmation delay —
  labelled "modelled" in every receipt, because no chain is contacted.
- **Paper P&L report**: per-position unrealised P&L at current paper
  prices plus realised total and paper balance.

## Safety limits (read before forking this for real use)

- No wallet creation, no private-key handling, no seed phrases, no RPC
  URL, no mainnet flag — there is nothing to "switch on" for real money.
- The checks are **simulated from the mint's hash**, not real on-chain
  simulation. A real deployment must replace `token_checks.py` with a
  real forked-state sell simulation (or a paid API) before touching any
  real funds — and that replacement is deliberately out of scope here.
- Prices are simulated, not market data. P&L figures prove the pipeline
  works, not that any strategy is profitable.

## Project layout

```
call_parser.py     Parse token calls: mint / symbol / chain / size
paper_trader.py    Seeded paper market, paper wallet, receipts, P&L
token_checks.py    SIMULATED honeypot/rug checks (PASS / WARN / BLOCK)
bot.py             python-telegram-bot wiring: commands + call handler
demo.py            Offline CLI: one full scripted paper session
tests/             pytest suite (parser, trader, checks, bot wiring)
```

## 1. Get a bot token from BotFather

1. Open Telegram and search for **@BotFather** (the official one, with
   the blue checkmark).
2. Send `/newbot`, pick a display name and a username ending in `bot`.
3. BotFather replies with a token like `123456789:AAE...` — copy it.
   Keep it secret: anyone with the token controls your bot.

## 2. Install and configure

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then paste your token into .env
```

## 3. Run

```bash
python bot.py
```

Post a token call in the channel (or to the bot), e.g.:

```
🚀 NEW CALL $MOON
CA: Moon7111111111111111111111111111111111111111
buy 1.5 SOL
```

The bot replies with the SIMULATED check result and the paper receipt,
or with a BLOCK / "no contract" skip message. The `.env` file is
git-ignored by default; only the placeholder `.env.example` ships.

## Commands

| Command      | What it does                              |
|--------------|-------------------------------------------|
| `/start`     | Welcome message + call format             |
| `/balance`   | Paper SOL balance + open position count   |
| `/positions` | Open paper positions                      |
| `/pnl`       | Paper P&L report (realised + unrealised)  |
| `/help`      | List commands                             |

## Try it offline — demo

No token, no network: one scripted channel call through the real
parser, SIMULATED checks and paper trader, with 10 market ticks and a
full sell + P&L report.

```bash
python demo.py
```

Output (verbatim from a real run):

```
=== TELEGRAM SNIPER BOT - PAPER DEMO (offline, no real funds) ===

[Channel post]
🚀 NEW CALL $MOON
CA: Moon7111111111111111111111111111111111111111
buy 1.5 SOL

Parsed call: mint=Moon7111111111111111111111111111111111111111 symbol=MOON chain=SOL size=1.5 SOL

SIMULATED checks for MOON:
  buy tax: 1.6% (simulated)
  sell tax: 1.6% (simulated)
  simulated sell test: OK (simulated)
  liquidity: OK (simulated)
  verdict: PASS

BUY MOON (PAPER)
  size: 1.5000 paper SOL @ 0.00000317 SOL
  qty: 472669.66 | fee: 0.0037 | slippage: 0.18%
  latency: 0.01 ms processing (measured) + 1016 ms confirm (modelled)

After 10 ticks: 0.00000307 SOL (entry was 0.00000317 SOL)

SELL MOON (PAPER)
  size: 1.4457 paper SOL @ 0.00000307 SOL
  qty: 472669.66 | fee: 0.0036 | slippage: 0.18%
  latency: 0.01 ms processing (measured) + 1016 ms confirm (modelled)
  realized P&L: -0.0543 paper SOL

PAPER P&L REPORT (no real funds)
  realised: -0.0543 paper SOL
  unrealised: +0.0000 paper SOL
  total: -0.0543 paper SOL
  paper balance: 99.9457 paper SOL

=== END DEMO - everything above was paper, nothing real moved ===
```

(The demo session loses a little paper SOL to fees and a down-tick —
that is the point: the pipeline, not a winning strategy, is what is
being demonstrated.)

## Tests

Everything except the live Telegram polling runs offline:

```bash
python -m pytest tests/ -v
```

Covered: call parsing (EVM / SOL / symbol-only / sizes / garbage),
paper buy/sell math (fees, slippage cap, partial sells, insufficient
balance), seeded-market determinism, all three SIMULATED-check verdict
branches, and the offline python-telegram-bot Application build
(6 handlers) plus the friendly no-token exit.

## License

MIT — a solid starting point for a real sniper bot's pipeline, with
paper trading as the only mode.
