import akshare as ak
import time

def test_one(code):
    try:
        print(f"Requesting {code}...")
        df = ak.fund_value_estimation_em(symbol=code)
        print(f"Result for {code}: {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"Error for {code}: {e}")

if __name__ == "__main__":
    test_one("001186")
