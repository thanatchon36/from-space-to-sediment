"""From Space to Sediment command line: fs2s <command> (or python -m from_space_to_sediment.cli <command>)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import PAPER_DIR, RESULTS_DIR, RIVERS_JSON, ROOT, SYNTHETIC_DIR


def _verify_argv(d: Path, out: Path, n_perm: int) -> list[str]:
    return [
        "--candidates", str(d / "candidates.csv"), "--factories", str(d / "diw_factories.csv"),
        "--known", str(d / "known_sites.csv"), "--negatives", str(d / "hard_negatives.csv"),
        "--labels", str(d / "labels.csv"), "--rivers", str(d / "rivers.geojson"),
        "--stations", str(d / "stations.csv"), "--matrix", "sediment", "--cores", str(d / "cores.csv"),
        "--outdir", str(out), "--n-perm", str(n_perm),
    ]


def cmd_synthetic(args):
    from .synthetic import generate

    out = generate(Path(args.out))
    print(f"synthetic test data written to {out.resolve()} (pipeline tests only, not real data)")


def cmd_selftest(args):
    from . import verify_trace
    from .synthetic import generate

    d = generate(Path(args.out))
    return verify_trace.main(_verify_argv(d, d / "out", args.n_perm))


def cmd_network(args):
    from .sim_validate import run

    _need_rivers(args.rivers_json)
    run(-1, out=args.out, rivers_json=args.rivers_json)


def cmd_sim(args):
    from .sim_validate import run

    _need_rivers(args.rivers_json)
    for s in args.scenario:
        run(s, reps=args.reps, n_perm=args.n_perm, out=args.out, rivers_json=args.rivers_json)


def cmd_figures(args):
    scripts = sorted((PAPER_DIR / "figures_src").glob("fig*.py"))
    for f in scripts:
        print(f"== {f.name}", flush=True)
        subprocess.run([sys.executable, str(f)], cwd=ROOT, check=True)
    print(f"{len(scripts)} figure scripts run; outputs in {PAPER_DIR / 'figures'}")


def cmd_paper(args):
    from .paper_build import build_paper
    from .paper_web import build_web

    print(f"wrote {build_paper()}")
    print(f"wrote {build_web()}")


def cmd_web(args):
    from .paper_web import build_web

    print(f"wrote {build_web()}")


def _need_rivers(path):
    if not Path(path).exists():
        raise SystemExit(f"{path} not found: run `make data` (scripts/download_data.py) first")


def main(argv=None):
    p = argparse.ArgumentParser(prog="fs2s", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synthetic", help="write the synthetic end-to-end test data set")
    s.add_argument("--out", default=str(SYNTHETIC_DIR))
    s.set_defaults(func=cmd_synthetic)

    s = sub.add_parser("selftest", help="synthetic data + verification and attribution -> <out>/out")
    s.add_argument("--out", default=str(SYNTHETIC_DIR))
    s.add_argument("--n-perm", type=int, default=199)
    s.set_defaults(func=cmd_selftest)

    s = sub.add_parser("verify", add_help=False,
                       help="verification and downstream attribution on your own data (fs2s verify --help)")
    s.set_defaults(func=None)

    for name, func, h in (("network", cmd_network, "network checks on the real Bang Pakong network"),
                          ("sim", cmd_sim, "Monte Carlo validation scenarios")):
        s = sub.add_parser(name, help=h)
        s.add_argument("--out", default=str(RESULTS_DIR))
        s.add_argument("--rivers-json", default=str(RIVERS_JSON))
        if name == "sim":
            s.add_argument("--scenario", type=int, nargs="+", default=[0, 1, 2, 3], choices=range(4))
            s.add_argument("--reps", type=int, default=150)
            s.add_argument("--n-perm", type=int, default=99)
        s.set_defaults(func=func)

    sub.add_parser("figures", help="redraw every paper figure").set_defaults(func=cmd_figures)
    sub.add_parser("paper", help="paper.md -> paper.tex -> paper.pdf, then the web reader").set_defaults(func=cmd_paper)
    sub.add_parser("web", help="web reader only -> docs/paper/index.html").set_defaults(func=cmd_web)

    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["verify"]:                 # pass every option straight through
        from . import verify_trace

        return verify_trace.main(argv[1:])
    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
