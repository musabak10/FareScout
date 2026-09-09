# FareScout ✈️

**FareScout** is a command-line tool that searches one-way flight fares across Turkish airports, converts prices to Turkish Lira using a live exchange rate, and shows you every flight that fits your budget — sorted from cheapest to most expensive.

## Features

- 🔍 Searches every airport combination for a given origin/destination city (e.g. Istanbul has both IST and SAW)
- 💱 Converts USD fares to TRY using a live exchange rate
- 💰 Filters results by your maximum budget
- 🔁 Automatic retries with timeout handling for flaky network requests
- 🧱 Clean, modular code that's easy to extend
- 🔐 API key is loaded from an environment variable, never hardcoded

## Requirements

- Python 3.8+
- An [Ignav](https://ignav.com) API key

## Installation

1. Clone the repository:
```bash
   git clone https://github.com/your-username/farescout.git
   cd farescout
```

2. Install dependencies:
```bash
   pip install -r requirements.txt
```

3. Set up your API key:
```bash
   cp .env.example .env
```
   Then open `.env` and replace `your_ignav_api_key_here` with your real API key.

## Usage

Run the script:

```bash
python farescout.py
```

You'll be prompted for:
