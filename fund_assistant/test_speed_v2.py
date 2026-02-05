
import akshare as ak
import time
import pandas as pd

def test_single_estimation():
    code = "000001"
    start = time.time()
    try:
        # Attempt 1: fund_value_estimation_em with symbol
        # Note: Documentation says symbol="全部" usually, let's see if it takes a code
        print(f"Testing fund_value_estimation_em('{code}')...")
        df = ak.fund_value_estimation_em(symbol=code)
        print(f"Result shape: {df.shape}")
        print(df.head())
    except Exception as e:
        print(f"fund_value_estimation_em failed for single code: {e}")
    print(f"Time: {time.time() - start:.4f}s")

def test_intraday_trend_last_point():
    code = "000001"
    start = time.time()
    try:
        # Attempt 2: Intraday trend
        print(f"Testing fund_open_fund_info_em('{code}', '单位净值估算走势')...")
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值估算走势")
        if not df.empty:
            print("Last point:")
            print(df.tail(1))
    except Exception as e:
        print(f"fund_open_fund_info_em failed: {e}")
    print(f"Time: {time.time() - start:.4f}s")

def test_bulk_fetch():
    start = time.time()
    try:
        print("Testing fund_value_estimation_em('全部')...")
        df = ak.fund_value_estimation_em(symbol="全部")
        print(f"Result shape: {df.shape}")
    except Exception as e:
        print(f"Bulk fetch failed: {e}")
    print(f"Time: {time.time() - start:.4f}s")

if __name__ == "__main__":
    print("--- Single Fetch Test ---")
    test_single_estimation()
    print("\n--- Intraday Trend Test ---")
    test_intraday_trend_last_point()
    print("\n--- Bulk Fetch Test ---")
    test_bulk_fetch()
