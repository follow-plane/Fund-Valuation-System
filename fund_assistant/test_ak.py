import akshare as ak

def test_ak_fund_estimation():
    print("Testing AkShare fund_value_estimation_em...")
    try:
        df = ak.fund_value_estimation_em(symbol="全部")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Data shape: {df.shape}")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ak_fund_estimation()
