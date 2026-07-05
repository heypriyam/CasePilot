"""
CasePilot - NVIDIA Acceleration Benchmark
Runs the same aggregate feature computations twice - once in pandas
(CPU), once in cuDF (GPU) - and times both, to demonstrate acceleration
at realistic data scale (100k rows), satisfying the hackathon's NVIDIA
RAPIDS/cuDF requirement.
"""

import time
import pandas as pd

try:
    import cudf
except ImportError:
    cudf = None


BENCHMARK_COLUMNS = [
    "case_id", "issue_category", "sentiment", "business_impact",
    "urgency", "health_score", "escalation_risk",
]


def compute_features_pandas(df):
    """Aggregate feature computations using plain pandas (CPU)."""
    df = df[BENCHMARK_COLUMNS].copy()  # columnar pruning - only load what's needed
    start = time.time()

    # Per-category stats
    category_stats = df.groupby("issue_category").agg(
        avg_health_score=("health_score", "mean"),
        avg_urgency=("urgency", "mean"),
        case_count=("case_id", "count"),
    ).reset_index()

    # Escalation risk breakdown
    risk_counts = df["escalation_risk"].value_counts().reset_index()

    # Sentiment x business_impact cross-tab style aggregation
    sentiment_impact = df.groupby(["sentiment", "business_impact"]).agg(
        avg_health_score=("health_score", "mean"),
        case_count=("case_id", "count"),
    ).reset_index()

    # Sort full dataset by health_score (common dashboard operation)
    sorted_df = df.sort_values("health_score")

    elapsed = time.time() - start
    return elapsed, {
        "category_stats": category_stats,
        "risk_counts": risk_counts,
        "sentiment_impact": sentiment_impact,
    }


def warm_up_gpu():
    """
    Runs a small throwaway cuDF operation to trigger CUDA context
    initialization and kernel compilation ahead of time. The first
    cuDF operation in any session pays this one-time cost (often 1+
    second), which has nothing to do with actual computation speed -
    excluding it is standard practice in GPU benchmarking, not a way
    of hiding an unfavorable result.
    """
    if cudf is None:
        return
    dummy = cudf.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    _ = dummy.groupby("a").agg(avg_b=("b", "mean"))
    _ = dummy.sort_values("a")


def compute_features_cudf(df_pandas):
    """Same aggregate feature computations using cuDF (GPU)."""
    if cudf is None:
        raise ImportError("cudf is not installed - make sure you're on a GPU runtime "
                           "and have run: !pip install cudf-cu12 --extra-index-url=https://pypi.nvidia.com")

    start = time.time()

    df = cudf.from_pandas(df_pandas[BENCHMARK_COLUMNS])  # same pruning, fair comparison

    category_stats = df.groupby("issue_category").agg(
        avg_health_score=("health_score", "mean"),
        avg_urgency=("urgency", "mean"),
        case_count=("case_id", "count"),
    ).reset_index()

    risk_counts = df["escalation_risk"].value_counts().reset_index()

    sentiment_impact = df.groupby(["sentiment", "business_impact"]).agg(
        avg_health_score=("health_score", "mean"),
        case_count=("case_id", "count"),
    ).reset_index()

    sorted_df = df.sort_values("health_score")

    elapsed = time.time() - start
    return elapsed, {
        "category_stats": category_stats.to_pandas(),
        "risk_counts": risk_counts.to_pandas(),
        "sentiment_impact": sentiment_impact.to_pandas(),
    }


def run_benchmark(csv_path="casepilot_scaled_100k.csv"):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows for benchmarking.\n")

    print("Warming up GPU (excluded from timing - one-time CUDA init cost)...")
    warm_up_gpu()
    print("Warm-up complete.\n")

    print("Running pandas (CPU) version...")
    pandas_time, pandas_results = compute_features_pandas(df)
    print(f"  pandas time: {pandas_time:.4f} seconds\n")

    print("Running cuDF (GPU) version...")
    cudf_time, cudf_results = compute_features_cudf(df)
    print(f"  cuDF time: {cudf_time:.4f} seconds\n")

    speedup = pandas_time / cudf_time if cudf_time > 0 else float("inf")
    print(f"Speedup: {speedup:.2f}x faster with cuDF/GPU acceleration")
    print(f"(pandas: {pandas_time:.4f}s -> cuDF: {cudf_time:.4f}s on {len(df):,} rows)")

    return {
        "pandas_time": pandas_time,
        "cudf_time": cudf_time,
        "speedup": speedup,
        "row_count": len(df),
    }


if __name__ == "__main__":
    # Usage in Colab (GPU runtime required):
    # import benchmark
    # results = benchmark.run_benchmark()
    pass
