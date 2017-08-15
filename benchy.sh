#!/bin/bash
# ----------------------------------------------------------------------------
# Description   This is a simple script for benchmarking.
# Dependencies  none
#
# Date          2017-aug-11
# Author        Dimitar Misev
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# variables/constants
# ----------------------------------------------------------------------------

# Treat unset variables and parameters other than the special parameters ‘@’ or
# ‘*’ as an error when performing parameter expansion. An error message will be
# written to the standard error, and a non-interactive shell will exit.
set -u

# script name
readonly PROG=$(basename $0)

# benchmark configuration file
readonly BENCHMARK_CONF="benchmark.conf"

#
# benchmark.conf functions
#

# benchmark suite
readonly BEFORE_SUITE="before_suite"
readonly AFTER_SUITE="after_suite"
# benchmark groups
readonly BEFORE_GROUP="before_group"
readonly AFTER_GROUP="after_group"
# single benchmark
readonly IS_BENCHMARK="is_benchmark" # return 0 if the given file should be benchmarked, 1 otherwise
readonly RUN_BENCHMARK="run_benchmark"
readonly RUN_NON_BENCHMARK="run_non_benchmark"
readonly BEFORE_BENCHMARK="before_benchmark"
readonly AFTER_BENCHMARK="after_benchmark"
readonly BEFORE_BENCHMARK_REPEAT="before_benchmark_repetition"
readonly AFTER_BENCHMARK_REPEAT="after_benchmark_repetition"

readonly DEFAULT_BENCHMARK_REPEAT=5
readonly DEFAULT_BENCHMARK_RETRY=3

readonly DEFAULT_RESULTS_PATH=/tmp

# return codes
readonly RC_OK=0    # everything went fine
readonly RC_ERROR=1 # something went wrong

# determine script directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ] ; do SOURCE="$(readlink "$SOURCE")"; done
readonly SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

# ----------------------------------------------------------------------------
# functions
# ----------------------------------------------------------------------------

usage()
{
  local -r usage="
Usage: $PROG -d <benchmark_suite_path> [OPTION]...

A generic and flexible tool for setting up macro/system benchmarks.

Options:
  -d, --suite-path
    directory containing the benchmark suite to be evaluated
  -r, --results-path
    benchmark results will be saved in a timestamped subdirectory of the
    directory specified with this argument; by default this is /tmp
  --init
    initialize new benchmark suite; the path specified with -d must be an
    empty directory in this case
  --quiet
    do not print any messages, except for errors
  -h, --help
    display this help and exit
"

  echo "$usage"
  exit $RC_OK
}

# logging
timestamp() {
  date +"%y-%m-%d %T"
}

log_header() {
  echo "[`timestamp`] $PROG:"
}

error()
{
  echo >&2 $(log_header) "$@"
  echo >&2 $(log_header) exiting.
  exit $RC_ERROR
}

error_and_usage()
{
  echo >&2 $(log_header) "$@"
  usage
}

print_msg()
{
  [ -z "$quiet" ] && echo "$@"
}

check()
{
  if [ $? -ne 0 ]; then
    print_msg failed.
  else
    print_msg ok.
  fi
}

log()
{
  print_msg $(log_header) "$@"
}

logn()
{
  print_msg -n $(log_header) "$@"
}

get_number_variable()
{
  local -r default_value="$1"
  local -r custom_value="$2"
  local ret=$default_value
  # provided by some benchmark.conf
  if [ -n "$custom_value" ]; then
    [ ! -z "${custom_value##*[!0-9]*}" ] || \
      error "Non-number value '$custom_value'.";
    ret=$custom_value
  fi
  echo $ret
}

# return 0 if the given function name is defined, or 1 otherwise
function_defined()
{
  local -r function_name="$1"
  declare -f "$function_name" > /dev/null
}

execute_if_defined()
{
  local -r function_name="$1"
  shift
  if function_defined "$function_name"; then
    $function_name "$@"
  fi
}

on_exit()
{
  if [ -n "$suite_datadir" -a -d "$suite_datadir" ]; then
    log "All measurements have been saved at '$suite_datadir'."
  fi
  log "Done, exiting."
}

trap on_exit EXIT

# ----------------------------------------------------------------------------
# parse command-line arguments
# ----------------------------------------------------------------------------

# @global variable
suite_path=
# @global variable
results_path="$DEFAULT_RESULTS_PATH"
# @global variable
init_benchmark=
# @global variable
quiet=

parse_command_line_args()
{
  local option=""
  for i in "$@"; do

    if [ -n "$option" ]; then
      case $option in
        -d|--suite-path*)   suite_path="$i";;
        -r|--results-path*) results_path="$i";;
        *) error "unknown option: $option";;
      esac
      option=""

    else
      option=""
      case $i in
        -h|--help*)  usage;;
        --init*)     init_benchmark=1;;
        --quiet*)    quiet=1;;
        *)           option="$i";;
      esac
    fi

  done
}

verify_command_line_args()
{
  # verify the benchmark path is valid
  [ -n "$suite_path" ] || error_and_usage "Please specify a benchmarking path."
  suite_path=${suite_path%/}
  [ -d "$suite_path" ] || error_and_usage "Invalid directory '$suite_path'."
  [ -r "$suite_path" ] || \
    error_and_usage "User '$USER' has no read permissions for '$suite_path'."

  [ -d "$results_path" ] || error_and_usage "Invalid directory '$results_path'."
  [ -w "$results_path" ] || \
    error_and_usage "User '$USER' has no write permissions for '$results_path'."

  # make sure the benchmark directory to initialize is empty
  if [ -n "$init_benchmark" ]; then
    if find "$suite_path" -mindepth 1 | read; then
      error "Cannot initialize non-empty directory '$suite_path'."
    fi
  fi

  suite_path="$(readlink -f "$suite_path")"
}

# ----------------------------------------------------------------------------
# benchmark data directory
# ----------------------------------------------------------------------------

# @global variable
suite_datadir=
# @global variable
group_datadir=

init_suite_datadir()
{
  local -r suite_name="$1"
  local -r tstamp=$(date +"%y%m%d_%H%M%S")
  # make sure we have an absolute path
  suite_datadir="$(readlink -f "$results_path")"
  suite_datadir="$suite_datadir/benchy.$suite_name.$tstamp"
  mkdir "$suite_datadir" || \
    error "Failed creating benchmark results directory '$suite_datadir'."
}

add_group_datadir()
{
  local -r group_name="$1"
  group_datadir="$suite_datadir/$group_name"
  mkdir -p "$group_datadir"
}

# ----------------------------------------------------------------------------
# further functions
# ----------------------------------------------------------------------------

load_benchmark_conf()
{
  if [ -f "$BENCHMARK_CONF" ]; then
    logn "Loading benchmark configuration '$curr_directory/$BENCHMARK_CONF'... "
    . "$BENCHMARK_CONF"
    check
  fi
}

# for benchmark suite and groups
execute_start_end_function()
{
  local -r dir_name=$(basename "$curr_directory")
  if [ "$curr_directory" = "$suite_path" ]; then
    execute_if_defined "$1" "$dir_name"
  else
    execute_if_defined "$2" "$dir_name"
  fi
}

enter_dir()
{
  local -r new_dir="$1"
  local -r dir_name=$(basename "$new_dir")

  if [ -n "$curr_directory" ]; then
    log "Running benchmark group '$dir_name'..."
    add_group_datadir "$dir_name"
    curr_directory="$curr_directory/$new_dir"
  else
    log "Running benchmark suite '$dir_name'..."
    init_suite_datadir "$dir_name"
    curr_directory="$new_dir"
  fi
  echo "enter dir before: $PWD"
  pushd "$new_dir" > /dev/null
  echo "enter dir after: $PWD"
  load_benchmark_conf
  execute_start_end_function "$BEFORE_SUITE" "$BEFORE_GROUP"
}

exit_dir()
{
  execute_start_end_function "$AFTER_SUITE" "$AFTER_GROUP"
  echo "exit dir before: $PWD"
  popd
  echo "exit dir after: $PWD"
  curr_directory="$(dirname "$curr_directory")"

  # should we load the suite benchmark.conf again when exiting a group directory?
  # it's not easily possible to unload the group benchmark.conf if any was loaded
}

# ----------------------------------------------------------------------------
# result extraction, statistic calculation
# ----------------------------------------------------------------------------

readonly result_group_header="Benchmark,\
Mean execution time (s),Median execution time (s),Min execution time (s),Stddev time,\
Mean memory use (MB),Median memory use (MB),Min memory use (MB),Stddev memory use,\
Mean CPU use (%),Median CPU use (%),Min CPU use (%),Stddev CPU use"

aggregate_benchmark_results()
{
  local -r benchmark="$1"
  local -r group="$2"

  # aggregated results files
  local -r result_time="$group_datadir/$benchmark.time"
  local -r result_memory="$group_datadir/$benchmark.memory"
  local -r result_cpu_utilization="$group_datadir/$benchmark.cpu"
  local -r result_group="$group_datadir/$group.results.csv"

  local result

  # extract time, memory, cpu utilization, etc. for each benchmark repetition
  for result in "$group_datadir/$benchmark"-*; do
    # format: h:mm:ss or m:ss
    awk '/Elapsed \(wall clock\)/ { print $8; }' "$result" | \
      awk -F: 'END { if (NF > 2) printf("%.2f\n", $1 * 3600 + $2 * 60 + $3)
                 else printf("%.2f\n", $1 * 60 + $2) }' >> "$result_time"
    # format: X
    awk '/Maximum resident set size/ { print $6/1000; }' "$result" >> "$result_memory"
    # format: X%
    awk '/Percent of CPU/ { print $7; }' "$result" | tr -d '%' >> "$result_cpu_utilization"
  done

  # write header if not done already
  [ -f "$result_group" ] || echo "$result_group_header" > "$result_group"
  echo -n "$benchmark" >> "$result_group"

  # calculate statistics and add to the group results
  for result in "$result_time" "$result_memory" "$result_cpu_utilization"; do
    # sort results
    sort -g "$result" -o "$result"

    local avg=$(awk '{ sum += $1 } END { printf("%.2f", sum / NR) }' "$result")
    local median=$(awk '{ v[NR] = $1 }
      END { if (NR % 2) printf("%.2f", v[(NR + 1) / 2])
            else printf("%.2f", (v[(NR / 2)] + v[(NR / 2) + 1]) / 2.0) }' "$result")
    local min=$(head -n 1 "$result")
    local stddev=$(awk '{ sum += ($1 - '$avg')^2 }
      END { res = 0; if (NR > 1) res = sqrt(sum / (NR-1)); printf("%.2f", res) }' "$result")
    echo -n ",$avg,$median,$min,$stddev" >> "$result_group"
  done
  echo "" >> "$result_group"

  log "Added benchmark '$benchmark' results in '$result_group'."
}

readonly result_suite_header="Group,\
Mean execution time (s),Median execution time (s),Min execution time (s),\
Mean memory use (MB),Median memory use (MB),Min memory use (MB),\
Mean CPU use (%),Median CPU use (%),Min CPU use (%)"

aggregate_group_results()
{
  local -r group="$1"
  local -r suite=$(basename "$suite_path")

  local -r result_group="$group_datadir/$group.results.csv"
  local -r result_suite="$suite_datadir/$suite.results.csv"

  [ -f "$result_suite" ] || echo "$result_suite_header" > "$result_suite"
  echo -n "$group" >> "$result_suite"

  local i
  local param
  local field=1
  for param in {1..3}; do
    for i in {1..3}; do
      field=$(($field+1))
      local total=$(awk -F',' '{ sum += $'$field' }
        END { printf("%.2f", sum) }' "$result_group")
      echo -n ",$total" >> "$result_suite"
    done
    # skip the stddev field
    field=$(($field+1))
  done
  echo "" >> "$result_suite"

  log "Added group '$group' results to '$result_suite'."
}

readonly result_total_header="Suite,\
Mean execution time (s),Median execution time (s),Min execution time (s),\
Mean memory use (MB),Median memory use (MB),Min memory use (MB),\
Mean CPU use (%),Median CPU use (%),Min CPU use (%)"

aggregate_total_results()
{
  local -r suite=$(basename "$suite_path")

  local -r result_suite="$suite_datadir/$suite.results.csv"
  local -r result_total="$suite_datadir/$suite.total_results.csv"

  echo "$result_total_header" > "$result_total"
  echo -n "$suite" >> "$result_total"

  local i
  local param
  local field=1
  for param in {1..3}; do
    for i in {1..3}; do
      field=$(($field+1))
      local total=$(awk -F',' '{ sum += $'$field' }
        END { printf("%.2f", sum) }' "$result_suite")
      echo -n ",$total" >> "$result_total"
    done
  done
  echo "" >> "$result_total"

  log "Added total '$suite' results to '$result_total'."
}

# ----------------------------------------------------------------------------
# evaluation
# ----------------------------------------------------------------------------

execute_repetition()
{
  local -r benchmark="$1"
  local -r group="$2"
  local -r repetition="$3"

  execute_if_defined "$BEFORE_BENCHMARK_REPEAT" "$benchmark" "$group" "$repetition"

  local -r benchmark_retry=$(get_number_variable $DEFAULT_BENCHMARK_RETRY $BENCHMARK_RETRY)
  local -r time_output="$group_datadir/$benchmark-$repetition.result"

  # the workaround for running /usr/bin/time on bash functions comes from
  # https://askubuntu.com/questions/430194/no-such-file-or-directory-when-executing-usr-bin-time/431184#431184
  export -f "$RUN_BENCHMARK"
  local retry
  for retry in $(seq $benchmark_retry); do
    echo "$RUN_BENCHMARK $benchmark $group $repetition $group_datadir" | \
      /usr/bin/time -v -o "$time_output" /bin/bash && break
  done

  execute_if_defined "$AFTER_BENCHMARK_REPEAT" "$benchmark" "$group" "$repetition"
}

execute_benchmark()
{
  local -r benchmark="$1"
  local -r group="$2"

  execute_if_defined "$BEFORE_BENCHMARK" "$benchmark" "$group"

  local -r benchmark_repeat=$(get_number_variable $DEFAULT_BENCHMARK_REPEAT $BENCHMARK_REPEAT)

  if function_defined "$RUN_BENCHMARK"; then
    local repetition
    for repetition in $(seq $benchmark_repeat); do
      execute_repetition "$benchmark" "$group" "$repetition"
    done
  fi

  execute_if_defined "$AFTER_BENCHMARK" "$benchmark" "$group"

  aggregate_benchmark_results "$benchmark" "$group"
}

execute_group()
{
  local -r group="$1"

  echo "execute_group before enter: $PWD"
  enter_dir "$group"
  echo "execute_group after enter: $PWD"

  local f
  for f in *; do
    [ -f "$f" ] || continue
    [ "$f" != "$BENCHMARK_CONF" ] || continue

    if ! function_defined "$IS_BENCHMARK" || "$IS_BENCHMARK" "$f" "$group"; then
      execute_benchmark "$f" "$group"
    else
      execute_if_defined "$RUN_NON_BENCHMARK" "$f" "$group"
    fi
  done

  echo "execute_group before exit: $PWD"
  exit_dir
  echo "execute_group after exit: $PWD"
  aggregate_group_results "$group"
}

# @global variable
curr_directory=""

execute_suite()
{
  echo "execute_suite before enter: $PWD"
  enter_dir "$suite_path"
  echo "execute_suite after enter: $PWD"

  local group_dir
  for group_dir in *; do
    # skip non-directories
    [ -d "$group_dir" ] || continue


    echo "execute_suite before execute_group: $PWD"
    execute_group "$group_dir"
    echo "execute_suite after execute_group: $PWD"
  done

  echo "execute_suite before exit: $PWD"
  exit_dir
  echo "execute_suite after exit: $PWD"
  aggregate_total_results
  log "All benchmarks completted."
}

# ----------------------------------------------------------------------------
# initialize a benchmark suite
# ----------------------------------------------------------------------------

init_suite()
{
  logn "Initializing benchmark suite directory '$suite_path'... "
  mkdir -p "$suite_path/group_1"
  cat << 'EOF' > "$suite_path/$BENCHMARK_CONF"
#!/bin/bash

# ----------------------------------------------------------------------------
# variables
# ----------------------------------------------------------------------------

# Set the number of times to repeat a benchmark; the more times it is evaluated,
# the more accurate will the measurements be.
BENCHMARK_REPEAT=5

# the number of times to retry a benchmark when it fails (the run_benchmark
# function return non-zero).
BENCHMARK_RETRY=3

# ----------------------------------------------------------------------------
# benchmark functions
# ----------------------------------------------------------------------------

#
# check whether a file should be benchmarked; if undefined, all files are
# considered benchmarks. Typically here there could be a grep on the benchmark
# extension or name.
# return: 0 if a file should be benchmarked, non-zero otherwise
#
is_benchmark() {
  local -r benchmark="$1"
  local -r group="$2"
  # benchmark every file
  return 0
}

#
# run the executable that needs to be benchmarked
# return: 0 if the benchmark executed successfully, non-zero otherwise
#
run_benchmark() {
  local -r benchmark="$1"
  local -r group="$2"
  local -r repetition="$3"
  local -r group_datadir="$4"
  # add code to execute the benchmark, e.g. `./$benchmark` if the file is an
  # executable
}

#
# called when is_benchmark() returns non-zero for a particular benchmark
# return: 0 if a file should be benchmarked, non-zero otherwise
#
run_non_benchmark() {
  local -r benchmark="$1"
  local -r group="$2"
  # add code to execute file which is not supposed to be benchmarked
}

#
# executed before starting a benchmark evaluation
#
before_benchmark() {
  local -r benchmark="$1"
  local -r group="$2"
}

#
# executed when a benchmark evaluation is finished
#
after_benchmark() {
  local -r benchmark="$1"
  local -r group="$2"
}

#
# executed before starting a benchmark repetition
#
before_benchmark_repetition() {
  local -r benchmark="$1"
  local -r group="$2"
  local -r repetition="$3"
}

#
# benchmark (file) name, group name, repetition
#
after_benchmark_repetition() {
  local -r benchmark="$1"
  local -r group="$2"
  local -r repetition="$3"
}

# ----------------------------------------------------------------------------
# group functions
# ----------------------------------------------------------------------------

#
# executed before a new group is evaluated
#
before_group() {
  local -r group="$1"
}

#
# executed when a group evaluation is finished
#
after_group() {
  local -r group="$1"
}

# ----------------------------------------------------------------------------
# suite functions
# ----------------------------------------------------------------------------

#
# executed before starting the benchmark suite evaluation
#
before_suite() {
  local -r suite="$1"
}

#
# executed when the benchmark suite evaluation is finished
#
after_suite() {
  local -r suite="$1"
}

EOF

check
}

# ----------------------------------------------------------------------------
# begin work
# ----------------------------------------------------------------------------

parse_command_line_args "$@"
verify_command_line_args

if [ -n "$init_benchmark" ]; then
  init_suite
else
  execute_suite
fi

exit $RC_OK
