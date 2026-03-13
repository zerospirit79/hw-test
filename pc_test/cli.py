import argparse, json, sys, os
from .utils.logging import setup_logging
from .sysinfo import os_info
from .repo.alt_repo import configure_by_info, dist_upgrade
from .automation.batch import run_batch
from .testsuite.runner import run_suite

def main(argv=None):
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser(prog="pc-test", description="ALT compatibility testing tool (Python)")
    sub = ap.add_subparsers(dest="cmd")

    ap_detect = sub.add_parser("detect", help="Print detected OS/release info (JSON)")
    ap_detect.add_argument("--log-level", default="INFO")

    ap_repo = sub.add_parser("repo", help="Configure repositories based on detected release")
    ap_repo.add_argument("--source", choices=["internet","usb","lan"], default="internet")
    ap_repo.add_argument("--mirror-url", default=None)
    ap_repo.add_argument("--log-level", default="INFO")

    ap_up = sub.add_parser("upgrade", help="apt-get dist-upgrade -y")
    ap_up.add_argument("--log-level", default="INFO")

    ap_test = sub.add_parser("test", help="Run test suites")
    ap_test.add_argument("--suite", action="append", default=["basic"])
    ap_test.add_argument("--ctx", default=None, help="JSON context for tests")
    ap_test.add_argument("--log-level", default="INFO")

    ap_batch = sub.add_parser("batch", help="Batch mode (JSON profile)")
    ap_batch.add_argument("profile_json", help="Inline JSON or @path/to/file.json")
    ap_batch.add_argument("--log-level", default="INFO")

    args = ap.parse_args(argv)
    setup_logging(args.log_level if hasattr(args, "log_level") else "INFO")

    if args.cmd == "detect":
        info = os_info.collect()
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "repo":
        info = os_info.collect()
        configure_by_info(info, source=args.source, mirror_url=args.mirror_url)
        print("Repositories configured")
        return 0

    if args.cmd == "upgrade":
        dist_upgrade()
        print("System upgraded")
        return 0

    if args.cmd == "test":
        ctx = {}
        if args.ctx:
            ctx = json.loads(open(args.ctx[1:],encoding="utf-8").read()) if args.ctx.startswith("@") else json.loads(args.ctx)
        res = run_suite(args.suite, ctx)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "batch":
        pj = args.profile_json
        profile = json.loads(open(pj[1:],encoding="utf-8").read()) if pj.startswith("@") else json.loads(pj)
        report = run_batch(json.dumps(profile, ensure_ascii=False))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    ap.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
