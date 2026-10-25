// Original minimal producer used by the upstream-format integration check.
#include <benchmark/benchmark.h>
#include <numeric>
#include <vector>

static void BM_Sum(benchmark::State& state) {
  std::vector<int> values(static_cast<size_t>(state.range(0)), 7);
  for (auto _ : state) {
    auto sum = std::accumulate(values.begin(), values.end(), 0);
    benchmark::DoNotOptimize(sum);
  }
}
BENCHMARK(BM_Sum)->Arg(8)->Arg(64);
BENCHMARK_MAIN();
