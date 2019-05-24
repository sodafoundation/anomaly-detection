# Copyright 2019 The OpenSDS Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

from numpy import genfromtxt


def read(file_name, delimiter=',', skip_header=0, max_rows=10000):
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
    skip_header += 1  # for title
    return genfromtxt(file_path, delimiter=delimiter, skip_header=skip_header, max_rows=max_rows)

