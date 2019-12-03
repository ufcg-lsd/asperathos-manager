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

import logging
import os


class Log:
    def __init__(self, name, output_file_path):
        self._verify_existing_paths()
        self.logger = logging.getLogger(name)
        self.logger.propagate = False
        if not len(self.logger.handlers):
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            self.logger.addHandler(handler)
            handler = logging.FileHandler(output_file_path)
            self.logger.addHandler(handler)

    def log(self, text):
        self.logger.info(text)

    def _verify_existing_paths(self):
        if not os.path.exists('logs'):
            os.mkdir('logs')


def configure_logging():
    logging.basicConfig(level=logging.INFO)
