import requests
import json
import datetime

def test_eastmoney_api():
    """Test EastMoney API for on-exchange funds"""
    
    # Test fund codes
    test_codes = ['161226', '510300', '159915', '162411']
    
    for fund_code in test_codes:
        print(f"\n=== Testing {fund_code} ===")
        
        # Determine market
        market = '1' if fund_code.startswith(('5', '6')) else '0'
        
        # Construct API URL
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{fund_code}&fields=f43,f57,f58,f60,f169,f170,f124"
        
        # Headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "*/*"
        }
        
        try:
            print(f"URL: {url}")
            print(f"Market: {market}")
            
            response = requests.get(url, headers=headers, timeout=5.0)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if data.get('data'):
                    stock_data = data['data']
                    print(f"Current Price (f43): {stock_data.get('f43')}")
                    print(f"Pre-close (f60): {stock_data.get('f60')}")
                    print(f"Change % (f170): {stock_data.get('f170')}")
                    print(f"Time (f124): {stock_data.get('f124')}")
                    
                    # Calculate actual values
                    raw_latest = float(stock_data.get('f43', 0))
                    raw_pre_close = float(stock_data.get('f60', 0))
                    
                    latest = raw_latest / 10000.0 if raw_latest > 100 else raw_latest
                    pre_close = raw_pre_close / 10000.0 if raw_pre_close > 100 else raw_pre_close
                    pct = float(stock_data.get('f170', 0)) / 100.0
                    
                    print(f"Calculated - Latest: {latest}, Pre-close: {pre_close}, Change %: {pct}")
                else:
                    print("No data found in response")
            else:
                print(f"Error response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Other error: {e}")

if __name__ == "__main__":
    test_eastmoney_api()