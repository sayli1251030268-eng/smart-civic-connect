"""
Smart Civic Connect - High Concurrency Load Testing Harness
Simulates concurrent citizens accessing feeds, submitting complaints,
and testing API throughput & latency percentiles.

Run:
    python load_test.py [--concurrency 25] [--requests 200]
"""
import argparse
import asyncio
import io
import os
import random
import time
from PIL import Image
import httpx

os.environ["DATABASE_URL"] = "sqlite:///./load_test.db"
os.environ["AI_ENABLED"] = "off"
from app.database import Base, engine
from app.main import app
Base.metadata.create_all(engine)

def generate_sample_image(color="blue"):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, "PNG")
    return buf.getvalue()

CATEGORIES = ["pothole", "garbage", "streetlight", "water_leakage", "drainage"]
WARDS = ["Kothrud", "Shivajinagar", "Hadapsar", "Viman Nagar", "Baner", "Aundh"]

class LoadTestRunner:
    def __init__(self, target_url=None, concurrency=20, total_requests=100):
        self.target_url = target_url
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.latencies = []
        self.successes = 0
        self.failures = 0
        self.status_codes = {}

    async def worker(self, worker_id, queue, client):
        while not queue.empty():
            task_type = await queue.get()
            t0 = time.perf_counter()
            try:
                if task_type == "health":
                    res = await client.get("/health")
                elif task_type == "feed_all":
                    res = await client.get("/complaints?feed=all&limit=20")
                elif task_type == "feed_trending":
                    res = await client.get("/complaints?feed=trending&limit=20")
                elif task_type == "feed_nearby":
                    lat = 18.5204 + random.uniform(-0.02, 0.02)
                    lng = 73.8567 + random.uniform(-0.02, 0.02)
                    res = await client.get(f"/complaints?feed=nearby&lat={lat}&lng={lng}&radius_km=5")
                elif task_type == "categories":
                    res = await client.get("/categories")
                else:
                    res = await client.get("/updates")
                    
                elapsed = (time.perf_counter() - t0) * 1000
                self.latencies.append(elapsed)
                code = res.status_code
                self.status_codes[code] = self.status_codes.get(code, 0) + 1
                if 200 <= code < 400:
                    self.successes += 1
                else:
                    self.failures += 1
            except Exception as e:
                self.failures += 1
                self.status_codes["ERR"] = self.status_codes.get("ERR", 0) + 1
            finally:
                queue.task_done()

    async def run(self):
        queue = asyncio.Queue()
        tasks_pool = ["health", "feed_all", "feed_trending", "feed_nearby", "categories", "feed_all", "updates"]
        for _ in range(self.total_requests):
            queue.put_nowait(random.choice(tasks_pool))

        start_time = time.perf_counter()
        
        if self.target_url:
            async with httpx.AsyncClient(base_url=self.target_url, timeout=10.0) as client:
                workers = [asyncio.create_task(self.worker(i, queue, client)) for i in range(self.concurrency)]
                await queue.join()
                for w in workers:
                    w.cancel()
        else:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=10.0) as client:
                workers = [asyncio.create_task(self.worker(i, queue, client)) for i in range(self.concurrency)]
                await queue.join()
                for w in workers:
                    w.cancel()
                    
        total_time = time.perf_counter() - start_time
        self.print_report(total_time)

    def print_report(self, total_time):
        print("\n" + "=" * 55)
        print("     SMART CIVIC CONNECT - LOAD TEST RESULTS")
        print("=" * 55)
        print(f"Total Requests:       {len(self.latencies) + self.failures}")
        print(f"Concurrency Level:    {self.concurrency} workers")
        print(f"Total Time Taken:     {total_time:.2f} seconds")
        print(f"Throughput (RPS):     {(self.successes / max(total_time, 0.001)):.2f} req/sec")
        print(f"Successful Requests:  {self.successes}")
        print(f"Failed Requests:      {self.failures}")
        print(f"Status Code Breakdown: {self.status_codes}")

        if self.latencies:
            self.latencies.sort()
            avg = sum(self.latencies) / len(self.latencies)
            p50 = self.latencies[int(len(self.latencies) * 0.50)]
            p90 = self.latencies[int(len(self.latencies) * 0.90)]
            p95 = self.latencies[int(len(self.latencies) * 0.95)]
            p99 = self.latencies[min(int(len(self.latencies) * 0.99), len(self.latencies) - 1)]
            print("\nResponse Latencies (ms):")
            print(f"  Average:            {avg:.2f} ms")
            print(f"  Median (P50):       {p50:.2f} ms")
            print(f"  90th Percentile:    {p90:.2f} ms")
            print(f"  95th Percentile:    {p95:.2f} ms")
            print(f"  99th Percentile:    {p99:.2f} ms")
        print("=" * 55 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, default=None, help="Target URL (e.g. http://localhost:8000). Omit for in-memory ASGI.")
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--requests", type=int, default=150)
    args = parser.parse_args()

    runner = LoadTestRunner(target_url=args.url, concurrency=args.concurrency, total_requests=args.requests)
    asyncio.run(runner.run())
    if os.path.exists("load_test.db"):
        os.remove("load_test.db")
