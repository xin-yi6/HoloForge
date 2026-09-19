"""Dimensionless manufactured interval operator, not a HoloForge benchmark."""

import argparse
import json
import numpy as np
from scipy.linalg import eigh_tridiagonal


def spectrum(points, length, right):
    if type(points) is not int or points < 3 or not np.isfinite(length) or length <= 0:
        raise ValueError("Require at least three points and positive finite length")
    if right not in ("dirichlet", "neumann"):
        raise ValueError("Unknown right boundary condition")
    spacing = length / (points + (1 if right == "dirichlet" else 0.5))
    diagonal = np.full(points, 2.0)
    if right == "neumann":
        diagonal[-1] = 1.0  # Equal ghost and last values at the half-grid boundary.
    return (eigh_tridiagonal(diagonal, -np.ones(points - 1),
                            select="i", select_range=(0, 2))[0] / spacing**2).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=255)
    parser.add_argument("--length", type=float, default=1.0)
    parser.add_argument("--right", choices=("dirichlet", "neumann"), default="dirichlet")
    args = parser.parse_args()
    print(json.dumps({"points": args.points, "length": args.length, "right": args.right,
                      "eigenvalues": spectrum(args.points, args.length, args.right)}))


if __name__ == "__main__":
    main()
