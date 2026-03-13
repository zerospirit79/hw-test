#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import math
import json
import tempfile
import random
import shutil
import multiprocessing as mp
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

@dataclass
class BenchConfig:
    duration_s: int = 15
    cpus: int = 0            # 0 = auto
    ram_mb: int = 512        # per worker
    io_size_mb: int = 1024
    tmpdir: Optional[str] = None
    json_out: bool = False

@dataclass
class BenchResult:
    cpu_gops: float
    cpu_cores: int
    cpu_method: str
    ram_write_gbps: float
    ram_read_gbps: float
    ram_bytes: int
    io_write_gbps: float
    io_read_gbps: float
    io_path: str
    errors: List[str]

def _cpu_worker(stop_ts: float, seed: int, result_queue: mp.Queue) -> None:
    rnd = random.Random(seed)
    iters = 0
    a = rnd.random() + 1.0
    b = rnd.random() + 2.0
    c = rnd.random() + 3.0
    ops = 0
    while time.time() < stop_ts:
        a = math.sin(a) * math.cos(b) + math.tan(c)
        b = math.sqrt(abs(a*b)+1e-9) + math.log1p(abs(c)+1e-9)
        c = (a*b)/(c+1.0) + 1.0
        iters += 1
        ops += 20
        if iters % 1000 == 0:
            a += rnd.random()*1e-6
    # перед выходом возвращаем общий счёт
    result_queue.put(ops)

def run_cpu(duration_s: int, cpus: int) -> Tuple[float, int, str]:
    cores = cpus if cpus and cpus > 0 else (os.cpu_count() or 1)
    q = mp.Queue()
    stop_ts = time.time() + max(1, int(duration_s))
    procs = []
    for i in range(cores):
        p = mp.Process(target=_cpu_worker, args=(stop_ts, 12345 + i, q), daemon=True)
        p.start()
        procs.append(p)
    total_ops = 0
    for p in procs:
        p.join()
    # собрать все результаты
    while not q.empty():
        total_ops += q.get()
    duration_s = max(1.0, float(duration_s))
    gops = total_ops / duration_s / 1e9
    return gops, cores, "fp-mix"

def run_io(tmpdir: Optional[str], size_mb: int) -> Tuple[float, float, str]:
    size = max(1, int(size_mb)) * 1024 * 1024
    base = tmpdir or tempfile.gettempdir()
    d = tempfile.mkdtemp(prefix="bench_io_", dir=base)
    fpath = os.path.join(d, "io_test.bin")
    write_gbps = read_gbps = 0.0
    try:
        chunk = os.urandom(1024 * 1024)
        written = 0
        t0 = time.time()
        with open(fpath, "wb", buffering=0) as f:
            while written < size:
                remain = size - written
                n = f.write(chunk if remain >= len(chunk) else chunk[:remain])
                if n <= 0:
                    break
                written += n
            f.flush()
            os.fsync(f.fileno())
        t1 = time.time()
        dtw = max(1e-6, t1 - t0)
        write_gbps = (written / dtw) / 1e9

        read = 0
        t2 = time.time()
        with open(fpath, "rb", buffering=0) as f:
            while True:
                buf = f.read(1024 * 1024)
                if not buf:
                    break
                read += len(buf)
        t3 = time.time()
        dtr = max(1e-6, t3 - t2)
        read_gbps = (read / dtr) / 1e9
    finally:
        try:
            shutil.rmtree(d)
        except Exception:
            pass
    return write_gbps, read_gbps, base

def _ram_worker(n_bytes: int, result_queue: mp.Queue) -> None:
    block = os.urandom(4096)
    buf = bytearray(n_bytes)
    pos = 0
    blen = len(block)
    t0 = time.time()
    while pos < n_bytes:
        end = min(pos + blen, n_bytes)
        buf[pos:end] = block[: end - pos]
        pos = end
    t1 = time.time()
    # чтение
    s = 0
    pos = 0
    step = 4096
    mv = memoryview(buf)
    while pos < n_bytes:
        s ^= mv[pos]
        pos += step
    t2 = time.time()
    dtw = max(1e-6, t1 - t0)
    dtr = max(1e-6, t2 - t1)
    result_queue.put(((n_bytes / dtw), (n_bytes / dtr), s))

def run_ram(ram_mb: int, workers: int) -> Tuple[float, float, int]:
    per_worker = max(1, int(ram_mb)) * 1024 * 1024
    workers = max(1, int(workers))
    procs = []
    q = mp.Queue()
    for i in range(workers):
        p = mp.Process(target=_ram_worker, args=(per_worker, q), daemon=True)
        p.start()
        procs.append(p)
    write_bps = []
    read_bps = []
    for _ in procs:
        w, r, _ = q.get()
        write_bps.append(w)
        read_bps.append(r)
    for p in procs:
        p.join()
    total_bytes = per_worker * workers
    write_gbps = (sum(write_bps) / 1e9) if write_bps else 0.0
    read_gbps = (sum(read_bps) / 1e9) if read_bps else 0.0
    return write_gbps, read_gbps, total_bytes

def run(json_out: bool = False, duration: int = 15, cpus: int = 0, ram_mb: int = 512,
        io_size_mb: int = 1024, tmpdir: Optional[str] = None) -> int:
    cfg = BenchConfig(duration_s=duration, cpus=cpus, ram_mb=ram_mb, io_size_mb=io_size_mb, tmpdir=tmpdir, json_out=json_out)
    errors: List[str] = []
    # CPU
    try:
        cpu_gops, cpu_cores, cpu_method = run_cpu(cfg.duration_s, cfg.cpus)
    except Exception as e:
        errors.append(f"cpu: {e}")
        cpu_gops, cpu_cores, cpu_method = 0.0, (cfg.cpus or (os.cpu_count() or 1)), "error"
    # RAM
    try:
        ram_w_gbps, ram_r_gbps, ram_bytes = run_ram(cfg.ram_mb, max(1, cfg.cpus or (os.cpu_count() or 1)))
    except Exception as e:
        errors.append(f"ram: {e}")
        ram_w_gbps = ram_r_gbps = 0.0
        ram_bytes = 0
    # IO
    try:
        io_w_gbps, io_r_gbps, io_base = run_io(cfg.tmpdir, cfg.io_size_mb)
    except Exception as e:
        errors.append(f"io: {e}")
        io_w_gbps = io_r_gbps = 0.0
        io_base = cfg.tmpdir or tempfile.gettempdir()

    res = BenchResult(
        cpu_gops=cpu_gops,
        cpu_cores=cpu_cores,
        cpu_method=cpu_method,
        ram_write_gbps=ram_w_gbps,
        ram_read_gbps=ram_r_gbps,
        ram_bytes=ram_bytes,
        io_write_gbps=io_w_gbps,
        io_read_gbps=io_r_gbps,
        io_path=io_base,
        errors=errors
    )

    if json_out:
        print(json.dumps(asdict(res), ensure_ascii=False, indent=2))
    else:
        print("— CPU:")
        print(f" cores: {res.cpu_cores}, method: {res.cpu_method}, throughput: {res.cpu_gops:.3f} GOPS")
        print("— RAM:")
        print(f" total: {res.ram_bytes/1e6:.1f} MB, write: {res.ram_write_gbps:.3f} GB/s, read: {res.ram_read_gbps:.3f} GB/s")
        print("— I/O:")
        print(f" tmp: {res.io_path}, write: {res.io_write_gbps:.3f} GB/s, read: {res.io_read_gbps:.3f} GB/s")
        if errors:
            print("— Errors:")
            for e in errors:
                print(f" * {e}")
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(run())