#!/usr/bin/env python3
"""Regenerate the Manifesto measurement dashboard."""

from constraint_dashboard import render_dashboard


if __name__ == "__main__":
    render_dashboard()
    print("constraint-dashboard.html regenerated")
