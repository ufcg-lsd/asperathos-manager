# Copyright (c) 2017 UFCG-LSD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess

R_PREFIX = 'Rscript '
PYTHON_PREFIX = 'python '


def execute_r_script(script, args):
    command = R_PREFIX + script + " " + " ".join(args)
    p_status = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p_status.communicate()
    try:
        print(out, err)
        value = float(out)
        return value
    except Exception as e:
        print(e)
        print("Error message captured:", err)
        raise


def append_to_file(outfile, line):
    with open(outfile, 'a') as f:
        f.write(line)


def write_to_file(outfile, line):
    with open(outfile, 'w') as f:
        f.write(line)
