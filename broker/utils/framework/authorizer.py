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

import requests


def get_authorization(authorizer_url, username, password):
    format_data = (lambda user, pwd: "user=%s&pwd=%s" % (user, pwd))

    data = format_data(username, password)
    r = requests.post(authorizer_url, data=data)
    content_dict = eval(r.content.replace("true", "True").replace("false",
                                                                  "False"))

    return content_dict
