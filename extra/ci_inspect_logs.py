#!/usr/bin/env python3

from collections import defaultdict
import json
import os
import re
import sys

SKIP = -1           # Test was not performed
PASS = 0            # (PASS)  Compiled successfully
WARNING = 1         # (PASS)  Compiled with warnings
EXPECTED_ERROR = 2  # (PASS*) Compilation failed with expected errors
ERROR = 3           # (FAIL)  Compilation failed with errors
FAILURE = 4         # Test run failed to complete

TEST_LEGEND = [
        "Test passed successfully, with no warnings or errors.",
        "Test completed with some warnings; no errors detected.",
        "Test completed with errors, but all are known/expected.",
        "Test completed with unexpected errors.",
        "Test run failed to complete.",
        "Test was skipped." # -1
]

TEST_STATUS = [
    ":green_circle:",
    ":yellow_circle:",
    ":no_entry_sign:",
    ":red_circle:",
    ":fire:",
    ":new_moon:" # -1
]

BOARD_STATUS = [
    ":white_check_mark:",
    ":white_check_mark:*",
    ":heavy_check_mark:*",
    ":x:",
    ":fire:",
    ":new_moon:" # -1
]

# Single test data structure
class TestEntry:
    def __init__(self, artifact, board, sketch, status, issues):
        self.artifact = artifact
        self.board = board
        self.sketch = sketch
        self.status = status
        self.issues = issues

# Summary data structure
class TestGroup:
    def __init__(self, link=None):
        # Sets to track unique boards and sketches
        self.boards = set()
        self.sketches = set()
        # Counts of test results by status
        self.counts = { status : 0 for status in [PASS, WARNING, EXPECTED_ERROR, ERROR, FAILURE] }
        # Overall status of the group
        self.status = SKIP
        # Optional link to CI job
        self.link = link
        # List of individual test entries (all, only with issues)
        self.tests = []
        self.tests_with_issues = []

    def track(self, test_entry):
        # Update the group with a new test entry
        self.tests.append(test_entry)
        if test_entry.issues:
            self.tests_with_issues.append(test_entry)

        self.counts[test_entry.status] += 1
        self.status = max(self.status, test_entry.status)
        self.boards.add(test_entry.board)
        self.sketches.add(test_entry.sketch)

ARTIFACT_TESTS = defaultdict(TestGroup)            # { artifact: TestGroup() }
BOARD_TESTS = defaultdict(TestGroup)               # { board: TestGroup() }
SKETCH_TESTS = defaultdict(lambda: defaultdict(TestGroup)) # { artifact: { sketch: TestGroup() } }

def log_test(artifact, board, sketch, exceptions, status, issues, job_link=None):
    """
    Logs individual test results into the global test tracking structures.
    """

    # Ensure issues is a list
    if isinstance(issues, str):
        issues = [ issues ]

    # Adjust the status for expected errors
    if status == ERROR and any(pattern.match(sketch) for pattern in exceptions):
        status = EXPECTED_ERROR

    # Create the test entry
    test_entry = TestEntry(artifact, board, sketch, status, issues)

    # Track in global structures
    ARTIFACT_TESTS[artifact].track(test_entry)
    BOARD_TESTS[board].track(test_entry)
    SKETCH_TESTS[artifact][sketch].track(test_entry)

def print_test_matrix(artifact, artifact_boards, title, sketch_filter=lambda x: True):
    """
    Prints a matrix of test results for a given artifact and its boards. The
    sketch_filter function determines which sketches to include. No table is printed
    if no sketches pass the filter.
    """

    # Build the header row, which includes board names and board statuses.
    # Headers have a link to the board's CI job, if available.
    header_row = f"<tr><th colspan='2'><code>{artifact}</code> {title}</th>"
    for board in artifact_boards:
        res = BOARD_TESTS[board]
        header_col = f"<code>{board}</code>"
        if res.link:
            header_col = f"<a href='{res.link}'>{header_col}</a>"
        header_col += f"<br>{BOARD_STATUS[res.status]}"
        header_row += f"<th>{header_col}</th>"
    header_row += "</tr>"

    # Group sketches by library
    sketch_groups = {}
    for sketch in ARTIFACT_TESTS[artifact].sketches:
        res = SKETCH_TESTS[artifact][sketch]
        if not sketch_filter(res):
            continue

        #                   (1.................) (2....) (3................) (4.)
        match = re.search(r'(libraries|examples)/([^/]+)/(examples/|extras/)?(.*)', sketch)
        if match:
            group = match.group(2)
            sample = match.group(4)
        else:
            group = ""
            sample = sketch

        if group not in sketch_groups:
            sketch_groups[group] = []
        sketch_groups[group].append((sample, res))

    # Build the data rows, grouping libraries together. Each row corresponds to
    # a sketch, each cell to the test result icon of that sketch on that board.
    data_rows = []
    for group in sorted(sketch_groups.keys()):
        if group:
            data_rows.append(f"<tr><th colspan='2' align='left'><code>{group}</code></th><th colspan={len(artifact_boards)}><code>{group}</code></th></tr>")
            #data_rows.append(f"<tr><th colspan='2' align='left'><code>{group}</code></th>{''.join('<td align=center>---</td>' for x in artifact_boards)}</tr>")
        for sample, res in sorted(sketch_groups[group]):
            row_data = f"<tr><td>{TEST_STATUS[res.status]}</td>"
            # If there are issues, make the sketch name a link to the detailed logs below
            name_link = f"<code>{sample}</code>"
            if res.tests_with_issues:
                sketch = next(iter(res.sketches)) # only one
                sketch_id = sketch.replace('/', '_').replace(' ', '_').replace('-', '_')
                name_link = f"<a href='#user-content-{artifact}_{sketch_id}'>{name_link}</a>"
            row_data += f"<td>{name_link}</td>"

            for board in artifact_boards:
                test = next((test for test in res.tests if test.board == board), None)
                status = test.status if test else SKIP
                issues = test.issues if test else ""

                row_data += f"<td align='center'>{TEST_STATUS[status]}</td>"

            row_data += "</tr>"
            data_rows.append(row_data)

    if not data_rows:
        return

    # Print the table
    print("<table>")
    print(header_row)
    for row in data_rows:
        print(row)
    print("</table>\n")

    # Print detailed logs for sketches with issues
    for group in sorted(sketch_groups.keys()):
        for sample, res in sorted(sketch_groups[group]):
            if not res.tests_with_issues:
                continue

            # Header and anchor for the detailed logs
            sketch = next(iter(res.sketches)) # only one
            sketch_id = sketch.replace('/', '_').replace(' ', '_').replace('-', '_')
            print(f"<a name='{artifact}_{sketch_id}'></a>")
            print(f"<details name='{artifact}_{title}'><summary><code>{artifact}</code> logs for {TEST_STATUS[res.status]} <code>{group}</code> <code>{sample}</code></summary>")
            print("<blockquote><br><table>")

            # Test logs by board
            for test in sorted(res.tests_with_issues, key=lambda x: x.status, reverse=True):
                job_link = BOARD_TESTS[test.board].link
                test_text = f"<code>{test.board}</code>"
                if job_link:
                    test_text += f" (<a href='{job_link}'>full log</a>)"
                print(f"<tr><td>{TEST_STATUS[test.status]} {test_text}<br>\n\n```")
                for line in test.issues:
                    print(line)
                print("```\n</td></tr>")

            print("</table></blockquote></details>\n")

BOARD_MEM_REPORTS = defaultdict(dict) # { board: { region: [used, total] } }
BOARD_CONFIGS = defaultdict(dict)     # { board: { config_symbol: value } }
REGIONS_BY_SOC = defaultdict(set)    # { soc: set(regions) }

BASE_COLOR = 0x20
DELTA_COLOR = 0xff-2*BASE_COLOR

# percent is in range [0, 1] where 0 is good, 1 is bad
def color_cmd(percent):
    color_amt = int(DELTA_COLOR * percent)
    return f"\\color{{#{BASE_COLOR + color_amt:02x}{0xff - color_amt:02x}{BASE_COLOR:02x}}}"

def color_entry(values, full=True):
    if not values:
        return ""
    
    percent = values[0] / values[1]
    if full:
        return f"${{{color_cmd(percent)}\\frac{{{values[0]}}}{{{values[1]}}}\\space({percent*100:0.1f}\\\\%)}}$"
    else:
        return f"{'' if percent < 0.85 else ':warning:'} ${{{color_cmd(percent)}{percent*100:0.1f}\\\\%}}$"

def print_mem_report(artifact, artifact_boards):

    print("<table><tr>", end='')
    print("<th rowspan='2' colspan='2'>Board</th>", end='')
    print("<th rowspan='2'>SoC</th>", end='')
    print("<th rowspan='2'>FLASH</th>", end='')
    print("<th rowspan='2'>RAM</th>", end='')
    print("<th colspan='2'>User heaps</th>", end='')
    print("</tr>")
    print("<tr><th>SYS</th><th>LIBC</th><th>LLEXT</th><th>MBEDTLS</th></tr>")

    for soc, board in sorted((ALL_BOARD_DATA[board]['soc'], board) for board in artifact_boards):
        max_pct = max([ (BOARD_MEM_REPORTS[board][r][0] / BOARD_MEM_REPORTS[board][r][1]) for r in ('FLASH', 'RAM') ])
        icon = ':warning:' if max_pct > 0.85 else ''
        board_str = board.replace('_', '\\\\_')

        row = [
                icon,
                f"${{{color_cmd(max_pct)}\\texttt{{{board_str}}}}}$",
                f"<code>{soc}</code>",
                color_entry(BOARD_MEM_REPORTS[board]['FLASH']),
                color_entry(BOARD_MEM_REPORTS[board]['RAM']),
                f"${{{ BOARD_CONFIGS[board].get('CONFIG_HEAP_MEM_POOL_SIZE', 0) }}}$",
                f"${{{ BOARD_CONFIGS[board]['CONFIG_SRAM_SIZE']*1024 - BOARD_MEM_REPORTS[board]['RAM'][0] }}}$",
                f"${{{ BOARD_CONFIGS[board]['CONFIG_LLEXT_HEAP_SIZE']*1024 }}}$",
                f"${{{ BOARD_CONFIGS[board].get('CONFIG_MBEDTLS_HEAP_SIZE', '-') }}}$"
              ]
        
        print("<tr>")
        col_aligns = ['center', 'left', 'center', 'right', 'right', 'right', 'right', 'right', 'right']
        for index, cell in enumerate(row):
            print(f"<td align='{col_aligns[index]}'>\n\n{cell}\n\n</td>")
        print("</tr>")
    print("</table>")

    extra_data_present = False
    for soc in sorted(list(set([ ALL_BOARD_DATA[board]['soc'] for board in artifact_boards ]))):
        soc_boards = [ board for board in artifact_boards if ALL_BOARD_DATA[board]['soc'] == soc ]
        sorted_regions = sorted(r for r in REGIONS_BY_SOC[soc] if r not in ('FLASH', 'RAM'))
        if not sorted_regions:
            continue

        if not extra_data_present:
            print("<details><summary>SoC-specific data</summary><blockquote><br>\n")
            extra_data_present = True
 
        print(f"<table><tr><th rowspan='{len(soc_boards)+1}'><code>{soc}</code></th><th>Board</th>")
        for r in sorted_regions:
              print(f"<th>{r}</th>")
        print("</tr>")
        for board in sorted(soc_boards):
            print(f"<tr><th><code>{board}</code></th>")
            for r in sorted_regions:
                if r in BOARD_MEM_REPORTS[board]:
                    print(f"<td>\n\n{color_entry(BOARD_MEM_REPORTS[board][r])}\n\n</td>")
                else:
                    print(f"<td></td>")
            print("</tr>")
        print("</table>\n")
       # print()
       # for c in ('CONFIG_HEAP_MEM_POOL_SIZE', 'CONFIG_LLEXT_HEAP_SIZE', 'CONFIG_MBEDTLS_HEAP_SIZE'):
       #     if c in BOARD_CONFIGS[board]:
       #         print(f"{c:>25} {BOARD_CONFIGS[board][c]:8}")
       # print("</pre></td></tr>")

    if extra_data_present:
        print("</blockquote></details>")

# --- Main Logic ---

# Environment Variable Checks
ALL_BOARD_DATA_STR = os.environ.get('ALL_BOARD_DATA')
GITHUB_REPOSITORY = os.environ.get('GITHUB_REPOSITORY')
GITHUB_RUN_ID = os.environ.get('GITHUB_RUN_ID')

if not ALL_BOARD_DATA_STR or not GITHUB_REPOSITORY or not GITHUB_RUN_ID:
    print("Not in a Github CI run, cannot proceed.")
    sys.exit(0)

ALL_BOARD_DATA = json.loads(ALL_BOARD_DATA_STR)
ALL_BOARD_DATA = { b['board']: b for b in ALL_BOARD_DATA }

for board_data in ALL_BOARD_DATA.values():
    # Extract common fields
    artifact = board_data['artifact']
    board = board_data['board']
    variant = board_data['variant']
    subarch = board_data['subarch']
     
    # get board's config settings
    report_file = f"zephyr-{variant}.config"
    try:
        with open(report_file, 'r') as f:
            for line in f:
                if line.startswith('#') or '=' not in line:
                    continue
                sym, val = line.strip().split('=', 1)
                if val.startswith('"'):
                    BOARD_CONFIGS[board][sym] = val.strip('"')
                elif val=='y':
                    BOARD_CONFIGS[board][sym] = 1
                else:
                    BOARD_CONFIGS[board][sym] = eval(val)
    except Exception as e:
        log_test(artifact, board, 'CI test', [], FAILURE, f"Error reading config file: {e}")
        continue # Skip to the next board

    soc = BOARD_CONFIGS[board]['CONFIG_SOC']
    board_data['soc'] = soc

    # get board's memory report
    report_file = f"zephyr-{variant}.meminfo"
    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
    except Exception as e:
        log_test(artifact, board, 'CI test', [], FAILURE, f"Error reading mem report file: {e}")
        continue # Skip to the next board

    BOARD_MEM_REPORTS[board] = { region.replace(':',''): [used, total] for region, used, total in report_data }
    BOARD_MEM_REPORTS[board].pop('IDT_LIST', None)
    REGIONS_BY_SOC[soc].update(BOARD_MEM_REPORTS[board].keys())

    # Get list of expected errors for this board/variant
    exceptions = []
    if os.path.exists(f"variants/{variant}/known_example_issues.txt"):
        with open(f"variants/{variant}/known_example_issues.txt", 'r') as f:
            for line in f:
                sketch_pattern = line.split('#')[0].strip()
                if sketch_pattern:
                    exceptions.append(re.compile(f"^(ArduinoCore-zephyr/)?{sketch_pattern}"))

    # Get raw data from report file
    report_file = f"arduino-{subarch}-{board}.json"
    if not os.path.exists(report_file):
        log_test(artifact, board, 'CI test', [], FAILURE, "Report file not found.")
        continue # Skip to the next board

    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
    except Exception as e:
        log_test(artifact, board, 'CI test', [], FAILURE, f"Error reading report file: {e}")
        continue # Skip to the next board

    # Extract data from the report file
    job_id = report_data.get('job_id')
    job_link = f"https://github.com/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}/job/{job_id}#step:5" if job_id else None

    reports = report_data.get('boards', [{}])[0].get('sketches', [])
    if not reports:
        log_test(artifact, board, 'CI test', [], FAILURE, "Test report is empty, check CI log.", job_link)
        continue # Skip to the next board

    # Iterate through individual sketch reports
    for report in reports:
        sketch = report.get('name', 'unknown_sketch')
        success = report.get('compilation_success', False)
        issues = report.get('issues', [])

        # Replace long absolute paths with '...' for brevity.
        sketch_issues = [ re.sub(r'(/.+?)((/[^/]+){3}):', r'...\2:', issue) for issue in issues ]

        if not success:
            status = ERROR
        elif len(sketch_issues): # Implies warnings/non-critical issues
            status = WARNING
        else:
            status = PASS

        log_test(artifact, board, sketch, exceptions, status, sketch_issues, job_link)

ARTIFACTS = sorted(ARTIFACT_TESTS.keys())

# Begin output of the report
# --------------------------

ci_run_status = max(res.status for res in ARTIFACT_TESTS.values())
ci_run_passed = ci_run_status in (PASS, WARNING, EXPECTED_ERROR)
if ci_run_passed:
    title = "# CI run PASSED :green_circle:\n"
else:
    failed_boards = [ f"{BOARD_STATUS[res.status]} `{board}`" for board, res in BOARD_TESTS.items() if res.status in (ERROR, FAILURE) ]
    title = f"# CI run FAILED: {', '.join(failed_boards)}\n"
print(title)

# Print the recap table
print("<table>\n<tr><th>Artifact</th><th>Board</th><th>Status</th><th>RAM</th><th>Sketches</th><th>Warnings</th><th>Errors</th></tr>")

for artifact in ARTIFACTS:
    artifact_boards = sorted(ARTIFACT_TESTS[artifact].boards)
    artifact_status = ARTIFACT_TESTS[artifact].status

    first_line = True
    for board in artifact_boards:
        print(f"<tr>", f"<td rowspan='{len(artifact_boards)}'>{BOARD_STATUS[artifact_status]} <a href='#user-content-{artifact}'><code>{artifact}</code></a></td>" if first_line else "")
        first_line = False

        res = BOARD_TESTS[board]

        print(f"<td><code>{board}</code></td><td align='center'>{BOARD_STATUS[res.status]}</td>")
        if res.status == FAILURE:
            # only one test and one line in the issues array here
            print(f"<td colspan='4'>{res.tests[0].issues[0]}</td></tr>")
        else:
            print(f"<td align='right'>\n\n{color_entry(BOARD_MEM_REPORTS[board]['RAM'], False)}\n\n</td>")
            tests_str = len(res.tests) or "-"
            warnings_str = res.counts[WARNING] or "-"
            errors_str = f"<b>{res.counts[ERROR]}</b>" if res.counts[ERROR] else "-"
            if res.counts[EXPECTED_ERROR]:
                if errors_str == "-": # only expected errors
                    errors_str = f"<i>({res.counts[EXPECTED_ERROR]}*)</i>"
                else: # both actual and expected errors
                    errors_str += f" <i>(+{res.counts[EXPECTED_ERROR]}*)</i>"
            print(f"<td align='right'>{tests_str}</td><td align='right'>{warnings_str}</td><td align='right'>{errors_str}</td></tr>")
print("</table>\n")

# Print the legend
print("<details><summary>Legend</summary>")
print("<blockquote><br><table><tr><th align='center'>Board</th><th align='center'>Test</th><th>Status description</th></tr>")
for status in FAILURE, ERROR, EXPECTED_ERROR, WARNING, PASS, SKIP:
    print(f"<tr><td align='center'>{BOARD_STATUS[status]}</td>")
    print(f"<td align='center'>{TEST_STATUS[status]}</td>")
    print(f"<td>{TEST_LEGEND[status]}</td></tr>")
print("</table></blockquote></details>\n")

# Print artifact error warnings
for artifact in ARTIFACTS:
    artifact_boards = sorted(ARTIFACT_TESTS[artifact].boards)
    failed_boards = [ f"`{board}`" for board in artifact_boards if BOARD_TESTS[board].status in (ERROR, FAILURE) ]

    if failed_boards:
        print("> [!CAUTION]")
        print(f"> `{artifact}` is blocked due to failures on {', '.join(failed_boards)}!\n")

# Print the test matrix sections per artifact
for artifact in ARTIFACTS:
    artifact_boards = sorted([ board for board in ARTIFACT_TESTS[artifact].boards if BOARD_TESTS[board].status != FAILURE ])

    if not artifact_boards:
        continue

    print(f"<a name='{artifact}'></a>")
    print("\n---\n")
    print_test_matrix(artifact, artifact_boards, "issues", sketch_filter=lambda res: res.status in (ERROR, EXPECTED_ERROR))

    successful_tests = ARTIFACT_TESTS[artifact].counts[PASS] + ARTIFACT_TESTS[artifact].counts[WARNING]
    warning_tests = ARTIFACT_TESTS[artifact].counts[WARNING]
    if successful_tests:
        summary = f"{successful_tests} successful <code>{artifact}</code> tests hidden"
        if warning_tests:
            summary += f" ({warning_tests} with warnings)"

        print(f"<details><summary>{summary}</summary><blockquote><br>\n")
        print_test_matrix(artifact, artifact_boards, "tests", sketch_filter=lambda res: res.status in (PASS, WARNING))
        print("</blockquote></details>\n")

    print(f"<details><summary>Memory usage report for <code>{artifact}</code></summary><blockquote><br>")
    print_mem_report(artifact, artifact_boards)
    print("</blockquote></details>")

if not ci_run_passed:
    sys.exit(1)
