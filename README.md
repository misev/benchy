# benchy

This is a generic and flexible tool for setting up benchmarks. The benchmark is
self-contained in a single directory given as a parameter:

```bash
./benchy.sh -d <benchmark_path> [OPTION]...
```

The tool uses `/usr/bin/time` for instrumentation, and is probably not extremely
precise. It is mainly meant for quickly setting up system/macro benchmarks. The
main principles guiding its design are simplicity and ease of use. For now at 
least, benchy is a single script that depends on very standard Linux stuff: Bash
and awk.


## Nomenclature

- `Benchmark suite`: a collection of benchmark groups
- `Benchmark group`: a collection of benchmarks
- `Benchmark`: a single benchmark that is evaluated and for which execution time 
and other statistics are collected.


## Directory structure

The benchmark directory (`suite` below) should have a particular structure, e.g:

```bash
suite/
|-- group_1/
|   |-- benchmark_1.query
|   |-- benchmark_2.sh
|   |-- benchmark_3.jar
|   |-- benchmark.conf
|-- group_2/
|-- group_3/
|-- benchmark.conf
```

- directories (group_1, group_2, etc.) are equivalent 
to benchmark _groups_, so all related stuff that will be benchmarked should 
be put in the same directory. E.g, benchmarking 10 queries on growing data size 
could be put in one group.
- within a benchmark group we have files that can be executed as benchmarks
or as supplementary stuff before or after a benchmark (e.g. load data, prepare
system, etc.)
- `benchmark.conf` files are Bash scripts that customize how the benchmark is 
executed. There can be a `benchmark.conf` on suite level, as well as more 
specifc ones per group; in either case they are optional.

There is no restriction on how any file/directory is named with the exception
of `benchmark.conf`.


## benchmark.conf

`benchy.sh` provides just the functionality for timing, monitoring, averaging 
results, and aggregating them into a report. How the stuff that should be 
benchmarked is actually executed is specified by `benchmark.conf` configuration 
files.

`benchmark.conf` is a Bash script that can define particular variables and
functions. `benchy.sh` first loads the benchmark suite configuration, and then
as it goes through each group it loads its configuration as well if it
exists, allowing to override the suite-wide configuration with more specific
group configurations.

The variables and functions in `benchmark.conf` recognized in `benchy.sh` are
documented below.


### Variables

- `BENCHMARK_REPEAT`: the number of times to repeat a benchmark; the more times it is evaluated, the more accurate will the measurements be. By default five
repetitions are done.
- `BENCHMARK_RETRY`: the number of times to retry a benchmark when it fails
(`run_benchmark` return non-zero). By default three retries are attempted.


### Functions

Benchmark suite

- `on_suite_start`
    - _args_: suite name
    - _description_: executed before starting the benchmark suite evaluation
- `on_suite_end`
    - _args_: suite name
    - _description_: executed when the benchmark suite evaluation is finished

Benchmark groups

- `on_group_start`
    - _args_: group (directory) name
    - _description_: executed before a new group is evaluated
- `on_group_end`
    - _args_: group name
    - _description_: executed when a group evaluation is finished

Single benchmark

- `is_benchmark`
    - _args_: benchmark (file) name, group name
    - _return_: 0 if the given file should be benchmarked, non-zero otherwise
    - _description_: check whether a file should be benchmarked; if undefined,
    all files are considered benchmarks.
- `run_benchmark`
    - _args_: benchmark (file) name, group name, repetition
    - _return_: 0 if the benchmark executed successfully, non-zero otherwise
    - _description_: run the executable that needs to be benchmarked
- `run_non_benchmark`
    - _args_: benchmark (file) name, group name
    - _return_: 0 if it executed successfully, non-zero otherwise
    - _description_: run non-benchmark file
- `on_benchmark_start`
    - _args_: benchmark (file) name, group name
    - _description_: executed before starting a benchmark evaluation
- `on_benchmark_end`
    - _args_: benchmark (file) name, group name
    - _description_: executed when a benchmark evaluation is finished
- `on_benchmark_repeat_start`
    - _args_: benchmark (file) name, group name, repetition
    - _description_: executed before starting a benchmark repetition
- `on_benchmark_repeat_end`
    - _args_: benchmark (file) name, group name, repetition
    - _description_: executed when a benchmark repetition is finished
