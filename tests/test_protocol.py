"""Protocol draft (methodology 12.4/12.5) and fio summary (11.1.8)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hw_test.constants import TEST_BLOCKED, TEST_FAILED, TEST_PASSED, TEST_SKIPPED
from hw_test.fio_report import collect_fio_results, format_fio_table, parse_fio_log
from hw_test.protocol import build_rows, read_results, render_html, render_markdown

# Fragment of the example from methodology section 11.1.8
FIO_64K = """\
random-write-64k: (groupid=0, jobs=16): err= 0: pid=4363: Tue Aug 29 10:22:41 2023
  write: IOPS=19.2k, BW=1202MiB/s (1261MB/s)(352GiB/300038msec); 0 zone resets
    slat (usec): min=2, max=378504, avg=17.09, stdev=814.95
    clat (usec): min=150, max=701891, avg=26594.13, stdev=41064.37
     lat (usec): min=172, max=701908, avg=26611.31, stdev=41077.08
    clat percentiles (usec):
     |  1.00th=[ 1057],  5.00th=[ 1418], 10.00th=[ 1418], 20.00th=[ 1467],
   bw (  MiB/s): min=  113, max= 7251, per=100.00%, avg=1204.03, stdev=60.23, samples=9584
   iops        : min= 1814, max=116025, avg=19262.98, stdev=963.73, samples=9584
  lat (msec)   : 2=20.82%, 4=6.58%, 10=21.65%, 20=25.85%, 50=4.24%
  cpu          : usr=0.94%, sys=0.91%, ctx=5194503, majf=0, minf=226
"""

FIO_4K = """\
randow-write-4k: (groupid=0, jobs=1): err= 0: pid=1: Tue Aug 29 10:00:00 2023
  write: IOPS=27.5k, BW=108MiB/s (113MB/s)(31.5GiB/300001msec); 0 zone resets
    clat (nsec): min=1200, max=9000000, avg=33010.5, stdev=100.0
   bw (  KiB/s): min=1000, max=200000, avg=110123.31, stdev=10.0, samples=600
   iops        : min=  250, max=50000, avg=27530.83, stdev=10.0, samples=600
  cpu          : usr=5.45%, sys=9.65%, ctx=8278561, majf=0, minf=12
"""


class FioReportTests(unittest.TestCase):
    def test_parse_methodology_example(self) -> None:
        r = parse_fio_log("rndw-64k", FIO_64K)
        assert r is not None
        self.assertAlmostEqual(r.iops, 19262.98)
        self.assertAlmostEqual(r.bw_mib, 1204.03)
        self.assertAlmostEqual(r.clat_usec, 26594.13)
        self.assertEqual((r.cpu_usr, r.cpu_sys, r.cpu_ctx), (0.94, 0.91, 5194503))

    def test_units_are_normalized(self) -> None:
        r = parse_fio_log("rndw-4k", FIO_4K)
        assert r is not None
        self.assertAlmostEqual(r.clat_usec, 33.0105)
        self.assertAlmostEqual(r.bw_mib, 110123.31 / 1024)

    def test_failed_log_is_skipped(self) -> None:
        self.assertIsNone(parse_fio_log("seqr-1m", "fio: io_u error\nFAILED: 1\n"))

    def test_collect_in_methodology_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / "fio-sda"
            dev.mkdir()
            (dev / "rndw-64k.log").write_text(FIO_64K)
            (dev / "rndw-4k.log").write_text(FIO_4K)
            res = collect_fio_results(Path(tmp))
            self.assertEqual([r.test for r in res["sda"]], ["rndw-4k", "rndw-64k"])
            table = format_fio_table(res["sda"])
            self.assertIn("| rndw-64k | 19,262.98 | 1,204.03 | 26,594.13 |", table[3])


class ProtocolTests(unittest.TestCase):
    def make_workdir(self, tmp: str) -> Path:
        wd = Path(tmp)
        (wd / "STATE").mkdir()
        (wd / "STATE" / "RESULTS").write_text(
            f"{TEST_FAILED}\tcpupower\n{TEST_PASSED}\tsyslogs\n"
            f"{TEST_SKIPPED}\tfwupd\n{TEST_BLOCKED}\tglmark\n{TEST_PASSED}\tcpupower\n",
            encoding="utf-8",
        )
        (wd / "inxi-CM.txt").write_text("Machine:\n  Type: Laptop <x>\n", encoding="utf-8")
        (wd / "cpu-freq.txt").write_text("Без нагрузки: Core0: 800\n", encoding="utf-8")
        (wd / "comments-11.2.txt").write_text("llvmpipe", encoding="utf-8")
        (wd / "fio-sda").mkdir()
        (wd / "fio-sda" / "rndw-64k.log").write_text(FIO_64K)
        return wd

    def test_retest_overrides_previous_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_results(self.make_workdir(tmp))["cpupower"], TEST_PASSED)

    def test_rows_statuses_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = {r.number: r for r in build_rows(self.make_workdir(tmp))}
        self.assertEqual(rows["10.1"].status, "PASSED")
        self.assertEqual(rows["6"].status, "SKIPPED")
        self.assertEqual(rows["11.2"].status, "BLOCKED")
        self.assertEqual(rows["11.2"].comment, "llvmpipe")
        self.assertEqual(rows["3.3.1"].status, "")
        self.assertIn("# inxi -CM", rows["8.3.1"].evidence)
        self.assertTrue(any("rndw-64k" in e for e in rows["11.1"].evidence))

    def test_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rows = build_rows(self.make_workdir(tmp))
        title = [("Версия методики", "2.1 от 19.09.2023"), ("Ссылка на результаты", "<заполнить>")]
        md = render_markdown(title, rows)
        self.assertIn("| 10.1 | Проверка CPU под нагрузкой | PASSED |", md)
        self.assertIn("- 11.2. Производительность видеоподсистемы: BLOCKED — llvmpipe", md)
        page = render_html(title, rows)
        self.assertIn("Type: Laptop &lt;x&gt;", page)
        self.assertIn('<span class="todo">&lt;заполнить&gt;</span>', page)


if __name__ == "__main__":
    unittest.main()
