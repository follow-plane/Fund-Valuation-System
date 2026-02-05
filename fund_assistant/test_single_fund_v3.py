
import akshare as ak
import pandas as pd
import time

def test_specific_fund():
    code = "110011" # E Fund High Quality
    print(f"Testing {code}...")
    
    start = time.time()
    try:
        # Indicator: Unit NAV Estimation Trend
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值估算走势")
        print(f"Time: {time.time() - start:.4f}s")
        if not df.empty:
            print("Columns:", df.columns)
            print("Tail:", df.tail(1))
            # Check if we can extract current value
        else:
            print("Empty DataFrame returned.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_specific_fund()
